"""
Uploads data from CSV file with a given structure.
"""
import argparse
import pathlib

import psycopg2
import yaml
from psycopg2 import sql

FILE_PATH = pathlib.Path(__file__)
CONFIG_FILE_NAME = 'config.yaml'
CONFIG_PATH = FILE_PATH.parent.joinpath(CONFIG_FILE_NAME)


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('path', help='Path to CSV file.')
parser.add_argument('--schema', default='public', help='Schema to use.')
parser.add_argument('--table_name', default='de2_from_csv', help='Table name to use/create.')
parser.add_argument('--create_table', action='store_true', help='Whether to create table or not.')
parser.add_argument('--truncate', action='store_true', help='Whether to delete data before uploading.')


with open(CONFIG_PATH) as stream:
    config = yaml.safe_load(stream)

conn = psycopg2.connect(
    host=config['host'],
    port=config['port'],
    dbname=config['database'],
    user=config['user'],
    password=config['password'],
)


def check(table_name, schema):
    query = """
        SELECT count(*) FROM {}.{};
    """
    with conn.cursor() as cur:
        cur.execute(
            sql.SQL(query).format(sql.Identifier(schema), sql.Identifier(table_name))
        )
        res = cur.fetchone()
        print('total count:', res[0])


def create_table(table_name, schema):
    query = """
        CREATE TABLE IF NOT EXISTS {}.{} (
            "Date Received" 				date,
            "Product Name" 					text,
            "Sub Product" 					text,
            "Issue" 						text,
            "Sub Issue" 					text,
            "Consumer Complaint Narrative" 	text,
            "Company Public Response" 		text,
            "Company" 						text,
            "State Name" 					text,
            "Zip Code" 						text, 
            "Tags" 							text,
            "Consumer Consent Provided" 	text,
            "Submitted via" 				text,
            "Date Sent to Company" 			date,
            "Company Response to Consumer" 	text,
            "Timely Response" 				text,
            "Consumer Disputed" 			text,
            "Complaint ID" 					int
        );
    """
    with conn, conn.cursor() as cur:
        cur.execute(
            sql.SQL(query).format(sql.Identifier(schema), sql.Identifier(table_name)),
            (schema, table_name)
        )


def truncate_data(table_name, schema):
    query = """
        TRUNCATE TABLE {}.{} RESTART IDENTITY;
    """
    with conn, conn.cursor() as cur:
        cur.execute(sql.SQL(query).format(sql.Identifier(schema), sql.Identifier(table_name)))


def upload_data(path: str, table_name, schema, delimiter=','):
    query = """
        COPY {}.{} FROM %s DELIMITER %s CSV HEADER;
    """
    with conn, conn.cursor() as cur:
        cur.execute(
            sql.SQL(query).format(sql.Identifier(schema), sql.Identifier(table_name)),
            (path, delimiter)
        )


def main(args):
    print(args)
    if args.truncate:
        truncate_data(args.table_name, args.schema)
    if args.create_table:
        create_table(args.table_name, args.schema)
    upload_data(args.path, args.table_name, args.schema)
    check(args.table_name, args.schema)


if __name__ == '__main__':
    main(parser.parse_args())
