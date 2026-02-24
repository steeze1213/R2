import pymysql
from config import DB_CONFIG

def get_connection():
    return pymysql.connect(**DB_CONFIG)