#!/usr/bin/env python3

import argparse
import csv
import cx_Oracle
import math
import os
import pymysql
import re
import sys


limit = 10000

def connect(namespace):
    if not namespace:
        raise Exception(f"Namespace argument is required to read environment variables")

    client = os.environ.get(f"{namespace}_CLIENT")
    host = os.environ.get(f"{namespace}_HOST")
    port = os.environ.get(f"{namespace}_PORT")
    user = os.environ.get(f"{namespace}_USER")
    password = os.environ.get(f"{namespace}_PASSWORD")
    database = os.environ.get(f"{namespace}_DATABASE")

    if not client:
        raise Exception(f"Missing required value for '{namespace}_CLIENT'")
    if client not in ["mysql", "sqlplus"]:
        raise Exception(f"Unsuported client '{client}'")
    if not host:
        raise Exception(f"Missing required value for '{namespace}_HOST'")
    if not user:
        raise Exception(f"Missing required value for '{namespace}_USER'")
    if not password:
        raise Exception(f"Missing required value for '{namespace}_PASSWORD'")
    if not database:
        raise Exception(f"Missing required value for '{namespace}_DATABASE'")

    if not re.match(r"\d+", port):
        raise Exception(f"Port must be an integer: '{namespace}_PORT' {port}")
    port = int(port)

    try:
        if client == "mysql":
            conn = pymysql.connect(
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    database=database,
                    encoding="UTF-8",
                    cursorclass=pymysql.cursors.SSDictCursor
                    )
        elif client == "sqlplus":
            conn = cx_Oracle.connect(
                    user,
                    password,
                    f"{host}:{port}/{database}",
                    encoding="UTF-8"
                    )
    except Exception as e:
        raise Exception(f"Failed to connect for '{client}' to '{host}:{port}/{database}' as '{user}' (with password)") from e

    return conn


def fetch_table(namespace, table, start=0):
    if not re.match(r"[a-z0-9_]+", table):
        raise Exception(f"Invalid table name '{table}'")

    fetch(namespace, f"SELECT * FROM {table}", start)


def fetch(namespace, query, start=0):
    conn = connect(namespace)
    client = os.environ.get(f"{namespace}_CLIENT")
    writer = None
    offset = start
    with conn.cursor() as cur:
        if client == "sqlplus":
            user = os.environ.get(f"{namespace}_USER")
            owner = os.environ.get(f"{namespace}_OWNER", user)
            cur.execute(f"ALTER SESSION SET CURRENT_SCHEMA = {owner}")
        while True:
            if client == "mysql":
                cur.execute(f"{query} OFFSET {offset} LIMIT {limit}")
            elif client == "sqlplus":
                cur.execute(f"{query} OFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY")
                cur.rowfactory = lambda *args: dict(zip([d[0].lower() for d in cur.description], args))
            fieldnames = [d[0].lower() for d in cur.description]
            if not writer:
                writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames, delimiter='\t', lineterminator='\n')
                writer.writeheader()
            rows = cur.fetchall()
            writer.writerows(rows)
            if len(rows) < limit:
                return
            offset += limit


def main():
    parser = argparse.ArgumentParser(
            description="Connect to a MySQL database, run a query, and output TSV")
    parser.add_argument("namespace",
            type=str,
            help="The namespace for environment variables")
    parser.add_argument("table",
            type=str,
            help="The table to fetch")
    parser.add_argument("--offset",
            type=int,
            nargs="?",
            default=0,
            help="The offset to start at")
    args = parser.parse_args()

    fetch_table(args.namespace, args.table, args.offset)


if __name__ == "__main__":
    main()
