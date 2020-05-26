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
                    cursorclass=pymysql.cursors.SSDictCursor
                    )
            cur = conn.cursor()
        elif client == "sqlplus":
            conn = cx_Oracle.connect(
                    user,
                    password,
                    f"{host}:{port}/{database}",
                    encoding="UTF-8"
                    )
            cur = conn.cursor()
            user = os.environ.get(f"{namespace}_USER")
            owner = os.environ.get(f"{namespace}_OWNER", user)
            cur.execute(f"ALTER SESSION SET CURRENT_SCHEMA = {owner}")
    except Exception as e:
        raise Exception(f"Failed to connect for '{client}' to '{host}:{port}/{database}' as '{user}' (with password)") from e

    return cur


def fetch(cur, query, output=sys.stdout, start=0):
    writer = None
    offset = start
    while True:
        if isinstance(cur, cx_Oracle.Cursor):
            cur.execute(f"{query} OFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY")
            cur.rowfactory = lambda *args: dict(zip([d[0].lower() for d in cur.description], args))
        else:
            cur.execute(f"{query} LIMIT {limit} OFFSET {offset}")
        fieldnames = [d[0].lower() for d in cur.description]
        if not writer:
            writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter='\t', lineterminator='\n')
            writer.writeheader()
        rows = cur.fetchall()
        writer.writerows(rows)
        if len(rows) < limit:
            return
        offset += limit


def fetch_table(args):
    table = args.table
    if not re.match(r"[a-z0-9_]+", table):
        raise Exception(f"Invalid table name '{table}'")

    columns = "*"
    if table == "reference":
        # Some columns are private, so don't fetch them
        columns = "reference_id, reference_type, a_c_pathogen_flag, svm_classifier_score, curation_status, curation_keywords, production_flag"

    where = ""
    if args.references:
        refs = []
        with open(args.references, "r") as tsv:
            rows = csv.DictReader(tsv, delimiter='\t')
            for row in rows:
                if row["reference_id"]:
                    refs.append(row["reference_id"])
        refs = ", ".join(refs)
        where = f"WHERE reference_id IN ({refs})"

    query = f"SELECT {columns} FROM {table} {where}"

    with connect(args.namespace) as cur:
        fetch(cur, query, args.output)


def main():
    parser = argparse.ArgumentParser(
            description="Connect to a SQL database, run a query, and output TSV")
    parser.add_argument("namespace", help="The namespace for environment variables")
    parser.add_argument("table", help="The table to fetch")
    parser.add_argument("output",
            type=argparse.FileType("w"),
            nargs="?",
            default=sys.stdout,
            help="The file to write to")
    parser.add_argument("--references",
            nargs="?",
            help="The file with the list of references to fetch")
    parser.add_argument("--offset",
            type=int,
            nargs="?",
            default=0,
            help="The offset to start at")

    args = parser.parse_args()
    fetch_table(args)


if __name__ == "__main__":
    main()
