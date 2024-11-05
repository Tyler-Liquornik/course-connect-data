import yaml
from pymongo import MongoClient


def get_connection_string():
    with open("config.yaml") as file:
        config = yaml.safe_load(file)

    mongo_config = config["mongo"]
    connection_string = (
        f"mongodb+srv://{mongo_config['username']}:{mongo_config['password']}"
        f"@{mongo_config['cluster_url']}/{mongo_config['database']}?retryWrites=true&w=majority"
    )

    return connection_string


def get_mongo_client():
    connection_string = get_connection_string()
    return MongoClient(connection_string)


def get_database():
    client = get_mongo_client()
    with open("config.yaml") as file:
        config = yaml.safe_load(file)
    return client[config["mongo"]["database"]]
