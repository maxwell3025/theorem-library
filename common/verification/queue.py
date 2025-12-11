import pika

QUEUE_NAME = "verification_queue"


def get_channel():
    connection_parameters = pika.ConnectionParameters(host="rabbitmq")
    connection = pika.BlockingConnection(connection_parameters=connection_parameters)
    channel = connection.channel()
    return channel
