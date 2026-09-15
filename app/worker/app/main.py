import json
import logging
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pika
import redis
from prometheus_client import Counter, Histogram, generate_latest

from .config import get_settings

logger = logging.getLogger("worker")
settings = get_settings()

redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)

PROCESSED = Counter("worker_orders_processed_total", "Orders processed by worker", ["product_id"])
PROCESSING_TIME = Histogram("worker_processing_seconds", "Time to process one message", buckets=(0.1, 0.25, 0.5, 1, 2.5, 5))


def get_stats(redis_key: str, redis_field: str | None = None) -> int:
    try:
        if redis_field:
            value = redis_client.hget(redis_key, redis_field)
        else:
            value = redis_client.get(redis_key)
        return int(value or 0)
    except redis.RedisError:
        return 0


class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        if self.path != "/metrics":
            self.send_response(404)
            self.end_headers()
            return
        body = generate_latest()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):  # noqa: A003
        return


def run_metrics_server() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", 8000), MetricsHandler)
    logger.info("metrics server listening on :8000")
    server.serve_forever()


def process_message(body: bytes) -> None:
    event = json.loads(body)
    order_id = event["order_id"]
    product_id = event["product_id"]
    quantity = event["quantity"]

    with PROCESSING_TIME.time():
        time.sleep(settings.processing_seconds)

    PROCESSED.labels(product_id=str(product_id)).inc(quantity)
    redis_client.hincrby("orders:status", "processed", quantity)

    total = get_stats("stats:processed") or redis_client.incr("stats:processed")
    logger.info("Order %s (product=%s x%d) processed. Total processed=%s", order_id, product_id, quantity, total)


def on_message(channel, method, properties, body) -> None:
    try:
        process_message(body)
        channel.basic_ack(delivery_tag=method.delivery_tag)
    except Exception:
        logger.exception("Failed to process message, requeueing")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def main() -> None:
    logger.info("worker starting...")

    metrics_thread = threading.Thread(target=run_metrics_server, daemon=True)
    metrics_thread.start()

    connection = pika.BlockingConnection(pika.URLParameters(settings.rabbitmq_url))
    channel = connection.channel()
    channel.exchange_declare(exchange=settings.orders_exchange, exchange_type="topic", durable=True)
    channel.queue_declare(queue=settings.orders_queue, durable=True, arguments={"x-dead-letter-exchange": "dlx"})
    channel.exchange_declare(exchange="dlx", exchange_type="fanout", durable=True)
    channel.queue_bind(exchange=settings.orders_exchange, queue=settings.orders_queue, routing_key=settings.routing_key)
    channel.basic_qos(prefetch_count=settings.prefetch_count)
    channel.basic_consume(queue=settings.orders_queue, on_message_callback=on_message)
    logger.info("waiting for messages...")
    channel.start_consuming()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    main()