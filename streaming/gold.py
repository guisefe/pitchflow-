"""Gold: live football metrics from the Silver event stream."""
import logging
from delta.tables import DeltaTable
from pyspark.sql import DataFrame, SparkSession, functions as F
from streaming.config import CHECKPOINT_DIR, GOLD_DIR, SILVER_PATH
from streaming.metrics import win_probability, ATTACKING_TYPES
from streaming.session import get_spark

logger = logging.getLogger(__name__)
GOLD_SHOTS    = f"{GOLD_DIR}/shots"
GOLD_XG       = f"{GOLD_DIR}/xg_timeline"
GOLD_STATE    = f"{GOLD_DIR}/match_state"
GOLD_MOMENTUM = f"{GOLD_DIR}/momentum"
MOMENTUM_WINDOW_SECONDS = 5 * 60

def _exists(spark, path): return DeltaTable.isDeltaTable(spark, path)

def write_shots(df, batch_id):
    shots = df.filter(F.col("event_type") == "Shot").select(
        "event_id","team_name","player_name","minute",
        "match_second","loc_x","loc_y","xg","shot_outcome")
    if shots.isEmpty(): return
    shots.write.format("delta").mode("append") \
        .option("txnAppId","pitchflow-gold-shots") \
        .option("txnVersion", batch_id).save(GOLD_SHOTS)

def write_xg_timeline(df, batch_id, spark):
    xg = df.filter(F.col("xg") > 0).groupBy("team_name","minute").agg(
        F.sum("xg").alias("xg_batch"), F.count("*").alias("shots_batch"))
    if xg.isEmpty(): return
    if not _exists(spark, GOLD_XG):
        xg.withColumnRenamed("xg_batch","xg_total") \
          .withColumnRenamed("shots_batch","shots_total") \
          .write.format("delta").save(GOLD_XG); return
    DeltaTable.forPath(spark, GOLD_XG).alias("t") \
        .merge(xg.alias("s"),"t.team_name=s.team_name AND t.minute=s.minute") \
        .whenMatchedUpdate(set={"xg_total":"t.xg_total+s.xg_batch",
                                "shots_total":"t.shots_total+s.shots_batch"}) \
        .whenNotMatchedInsert(values={"team_name":"s.team_name","minute":"s.minute",
                                      "xg_total":"s.xg_batch","shots_total":"s.shots_batch"}) \
        .execute()

def write_match_state(df, batch_id, spark):
    sb = df.groupBy("team_name").agg(
        F.sum(F.when(F.col("shot_outcome")=="Goal",1).otherwise(0)).alias("batch_goals"),
        F.sum("xg").alias("batch_xg"), F.max("minute").alias("latest_minute"))
    if sb.isEmpty(): return
    if not _exists(spark, GOLD_STATE):
        sb.select(F.col("team_name"), F.col("batch_goals").alias("goals"),
                  F.col("batch_xg").alias("xg_total"), F.col("latest_minute"),
                  F.lit(0.5).alias("win_probability")) \
          .write.format("delta").save(GOLD_STATE); return
    DeltaTable.forPath(spark, GOLD_STATE).alias("t") \
        .merge(sb.alias("s"),"t.team_name=s.team_name") \
        .whenMatchedUpdate(set={"goals":"t.goals+s.batch_goals",
                                "xg_total":"t.xg_total+s.batch_xg",
                                "latest_minute":"s.latest_minute"}) \
        .whenNotMatchedInsert(values={"team_name":"s.team_name",
                                      "goals":"s.batch_goals","xg_total":"s.batch_xg",
                                      "latest_minute":"s.latest_minute",
                                      "win_probability":F.lit(0.5)}) \
        .execute()
    rows = {r["team_name"]: r for r in spark.read.format("delta").load(GOLD_STATE).collect()}
    if len(rows) == 2:
        t1, t2 = list(rows.keys())
        p1 = win_probability(int(rows[t1]["goals"]-rows[t2]["goals"]),
                             float(rows[t1]["xg_total"]-rows[t2]["xg_total"]),
                             max(0, 90-int(rows[t1]["latest_minute"])))
        DeltaTable.forPath(spark, GOLD_STATE).alias("t") \
            .merge(spark.createDataFrame([(t1,p1),(t2,round(1-p1,4))],
                   ["team_name","wp"]).alias("s"),"t.team_name=s.team_name") \
            .whenMatchedUpdate(set={"win_probability":"s.wp"}).execute()

def write_momentum(df, batch_id, spark):
    latest = df.agg(F.max("match_second")).collect()[0][0]
    if latest is None: return
    ws = max(0, int(latest) - MOMENTUM_WINDOW_SECONDS)
    recent = spark.read.format("delta").load(SILVER_PATH) \
        .filter((F.col("match_second") >= ws) & (F.col("match_second") <= latest))
    mom = recent.filter(F.col("event_type").isin(list(ATTACKING_TYPES))) \
                .groupBy("team_name").agg(F.count("*").alias("attacking_actions"))
    if mom.isEmpty(): return
    total = mom.agg(F.sum("attacking_actions")).collect()[0][0] or 1
    mom = mom.withColumn("dominance_pct", F.round(F.col("attacking_actions")/float(total),3)) \
             .withColumn("window_start_second", F.lit(ws)) \
             .withColumn("window_end_second", F.lit(int(latest)))
    if not _exists(spark, GOLD_MOMENTUM):
        mom.write.format("delta").save(GOLD_MOMENTUM); return
    DeltaTable.forPath(spark, GOLD_MOMENTUM).alias("t") \
        .merge(mom.alias("s"),"t.team_name=s.team_name") \
        .whenMatchedUpdateAll().whenNotMatchedInsertAll().execute()

def run():
    spark = get_spark("pitchflow-gold")
    stream = spark.readStream.format("delta").load(SILVER_PATH)
    def process_batch(df, batch_id):
        if df.isEmpty(): return
        df.cache()
        try:
            write_shots(df, batch_id)
            write_xg_timeline(df, batch_id, spark)
            write_match_state(df, batch_id, spark)
            write_momentum(df, batch_id, spark)
        finally: df.unpersist()
    query = (stream.writeStream.outputMode("append")
             .foreachBatch(process_batch)
             .option("checkpointLocation", f"{CHECKPOINT_DIR}/gold")
             .trigger(processingTime="5 seconds").start())
    logger.info("Gold stream started (Ctrl+C to stop)")
    query.awaitTermination()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
