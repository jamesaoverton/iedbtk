#!/usr/bin/env python3

import math
import sqlite3
import subprocess

from flask import Flask, request, redirect, Response, render_template
from requests import get, post
import tsv2rdf

#root = "/browse/"
root = "/"
data = tsv2rdf.readdir("data2")
sqlite = "file:build/iedb.db?mode=ro"
app = Flask(__name__, instance_relative_config=True)

assay_tables = {
    "bcell": {
        "title": "BCell",
        "columns": """
          bcell_id AS assay_id,
          reference_id,
          e_object_desc AS epitope,
          h_organism_name AS host,
          iv1_process_type
          iv1_imm_type,
          iv1_imm_object_organism_name,
          ant_object_desc,
          ant_object_mol_name,
          ant_object_organism_name,
          ant_type,
          as_type,
          as_type_response,
          as_char_value"""
    },
    "tcell": {
        "title": "TCell",
        "columns": """
          tcell_id AS assay_id,
          reference_id,
          e_object_desc AS epitope,
          h_organism_name AS host,
          iv1_process_type
          iv1_imm_type,
          iv1_imm_object_organism_name,
          ant_object_desc,
          ant_object_mol_name,
          ant_object_organism_name,
          ant_type,
          mhc_allele_name,
          as_type,
          as_type_response,
          as_char_value"""
    },
    "mhc_bind": {
        "title": "MHC Binding",
        "columns": """
          mhc_bind_id AS assay_id,
          reference_id,
          e_object_desc AS epitope,
          mhc_allele_name,
          as_type,
          as_type_response,
          as_char_value
          as_num_value"""
    },
    "mhc_elution": {
        "title": "MHC Elution",
        "columns": """
          mhc_elution_id AS assay_id,
          reference_id,
          e_object_desc AS epitope,
          h_organism_name AS host,
          iv1_process_type
          iv1_imm_type, iv1_imm_object_organism_name,
          ant_object_desc,
          ant_object_mol_name,
          ant_object_organism_name,
          ant_type,
          mhc_allele_name,
          as_type,
          as_type_response,
          as_char_value"""
    },
}
limit = 1000

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

@app.route('/favicon.ico')
def favicon():
    return ""

@app.route('/style.css')
def style():
    return """
#annotations {
  padding-left: 1em;
  list-style-type: none !important;
}
#annotations ul {
  padding-left: 3em;
  list-style-type: circle !important;
}
#annotations ul ul {
  padding-left: 2em;
  list-style-type: none !important;
}
#hierarchy {
  padding-left: 2.2em;
  list-style-type: circle !important;
}
#hierarchy ul {
  padding-left: 0.5em;
  list-style-type: circle !important;
}
""", 200, {"Content-Type": "text/css"}


@app.route('/')
def index():
    html = ["div",
            ["p", ["a", {"href": "/reference/"}, "References"]],
            ["p", ["a", {"href": "/assay/"}, "Assays"]],
            ["p", ["a", {"href": "/epitope/"}, "Epitopes"]],
            ["p", ["a", {"href": "/sqlite-web/"}, "SQL Browser"]]]
    return render_template("base.jinja2", html=tsv2rdf.render(html))

links = {
    "reference_id": "/reference/",
    "assay_id": "/assay/",
    "epitope_id": "/epitope/",
    "pubmed_id": "https://pubmed.ncbi.nlm.nih.gov/",
}

def make_paged_table(rows, count, page, link="?"):
    html = ["div"]
    nav = ["ul", {"class": "pagination", "style": "margin-top: 1em"}]
    cls = "page-item"
    if page == 1:
        cls += " disabled"
    nav.append(
        ["li",
         {"class": cls},
         ["a",
         {"class": "page-link", "href": f"{link}page={page - 1}"},
          "&laquo"]])
    for o in range(1, math.ceil(count/limit) + 1):
        cls = "page-item"
        if o == page:
            cls += " active"
        nav.append(
            ["li",
             {"class": cls},
             ["a",
             {"class": "page-link", "href": f"{link}page={o}"},
              str(o)]])
    cls = "page-item"
    if page == o:
        cls += " disabled"
    nav.append(
        ["li",
         {"class": cls},
         ["a",
         {"class": "page-link", "href": f"{link}page={page + 1}"},
          "&raquo;"]])
    html.append(nav)
    html.append(make_table(rows))
    return html


def make_table(rows):
    table = ["table", {"class": "table table-borderless"}]
    tr = ["tr"]
    for key in rows[0].keys():
        tr.append(["th", key])
    table.append(tr)
    for row in rows:
        tr = ["tr"]
        for key, value in row.items():
            if value and len(value) > 100:
                value = value[0:100] + "..."
            if key in links and links[key].startswith("http"):
                tr.append(["td", ["a", {"href": links[key] + value, "target": "_blank"}, value]])
            elif key in links:
                tr.append(["td", ["a", {"href": links[key] + value}, value]])
            else:
                tr.append(["td", str(value)])
        table.append(tr)
    return table


def make_kv(row):
    ul = ["ul", {"style": "list-style: none"}]
    for key, value in row.items():
        if value:
            ul.append(["li", ["strong", key], ": ", value])
    return ul


@app.route('/reference/')
def references():
    with sqlite3.connect(sqlite, uri=True) as conn:
        conn.row_factory = dict_factory
        cur = conn.cursor()
        table = "reference"
        cur.execute(f"SELECT count(*) AS count FROM {table}")
        row = cur.fetchone()
        count = row["count"]
        page = int(request.args.get("page", "1"))
        offset = (page - 1) * limit

        cur.execute(f"""SELECT reference_id,
            pubmed_id,
            article_authors AS author,
            article_title AS title,
            article_abstract AS abstract,
            article_date AS date
          FROM article
          UNION
          SELECT reference_id,
            pubmed_id,
            article_authors AS author,
            article_title AS title,
            article_abstract AS abstract,
            article_date AS date
          FROM article_dual
          UNION
          SELECT reference_id,
            "" AS pubmed_id,
            submission_authors AS author,
            submission_title AS title,
            submission_abstract AS abstract,
            substr(submission_date, 1, 4) AS date
          FROM submission
          ORDER BY reference_id
          LIMIT {limit}
          OFFSET {offset}""")
        html = ["div",
                ["h2", "References"],
                make_paged_table(cur.fetchall(), count, page)]
        return render_template("base.jinja2", html=tsv2rdf.render(html))


@app.route('/reference/<reference_id>')
def reference(reference_id):
    with sqlite3.connect(sqlite, uri=True) as conn:
        conn.row_factory = dict_factory
        cur = conn.cursor()
        html = ["div", ["h2", ["a", {"href": "./"}, "References"]]]

        cur.execute(f"SELECT * FROM reference WHERE reference_id = '{reference_id}'")
        row = cur.fetchone()
        html.append(["h3", f"Reference {reference_id}"])
        html.append(make_kv(row))

        for table, title in {"article": "Article", "article_dual": "Article", "submission": "Submission"}.items():
            cur.execute(f"SELECT * FROM {table} WHERE reference_id = '{reference_id}'")
            row = cur.fetchone()
            html.append(["h3", title])
            html.append(make_kv(row))

        for table, values in assay_tables.items():
            cur.execute(f"""SELECT {table}_id AS assay_id
              FROM {table}
              WHERE reference_id = '{reference_id}'
              ORDER BY assay_id""")
            items = []
            for row in cur:
                items.append(["li", ["a", {"href": "/assay/" + row["assay_id"]}, row["assay_id"]]])
            if len(items) > 0:
                items = ["ul"] + items
                html.append(["h3", values["title"], f" ({len(items)})"])
                html.append(items)

        cur.execute(f"""SELECT epitope_id
          FROM epitope
          WHERE reference_id = '{reference_id}'
          ORDER BY epitope_id""")
        items = []
        for row in cur:
            items.append(["li", ["a", {"href": "/epitope/" + row["epitope_id"]}, row["epitope_id"]]])
        if len(items) > 0:
            items = ["ul"] + items
            html.append(["h3", "Epitopes", f" ({len(items)})"])
            html.append(items)

        return render_template("base.jinja2", html=tsv2rdf.render(html))


@app.route('/assay/')
def assays():
    with sqlite3.connect(sqlite, uri=True) as conn:
        conn.row_factory = dict_factory
        cur = conn.cursor()
        html = ["div",
                ["h2", "Assays"]]
        nav = ["ul", {"class": "nav nav-tabs"}]
        tab = request.args.get("tab", "bcell")
        for table in assay_tables.keys():
            cls = "nav-link"
            if tab == table:
                cls += " active"
            if not "count" in assay_tables[table]:
                cur.execute(f"SELECT count(*) AS count FROM {table}")
                row = cur.fetchone()
                assay_tables[table]["count"] = row["count"]
            count = assay_tables[table]["count"]
            nav.append(
               ["li",
                {"class": "nav-item"}, 
                ["a",
                 {"class": cls, "href": f"?tab={table}"},
                 f"{assay_tables[table]['title']} ({count})"]])
        html.append(nav)

        table = tab
        count = assay_tables[table]["count"]
        page = int(request.args.get("page", "1"))

        offset = (page - 1) * limit
        values = assay_tables[table]
        cur.execute(f"""SELECT {values["columns"]}
          FROM {table}
          ORDER BY assay_id
          LIMIT {limit}
          OFFSET {offset}""")
        rows = cur.fetchall()
        if len(rows) > 0:
            html.append(make_paged_table(rows, count, page, f"?tab={table}&"))
        return render_template("base.jinja2", html=tsv2rdf.render(html))


@app.route('/assay/<assay_id>')
def assay(assay_id):
    with sqlite3.connect(sqlite, uri=True) as conn:
        conn.row_factory = dict_factory
        cur = conn.cursor()
        html = ["div", ["h2", ["a", {"href": "./"}, "Assays"]]]
        html.append(["h3", f"Assay {assay_id}"])

        for table in assay_tables.keys():
            cur.execute(f"SELECT * FROM {table} WHERE {table}_id = '{assay_id}'")
            row = cur.fetchone()
            if row:
                html.append(make_kv(row))
                epitope_id = row["epitope_id"]
                html += make_epitope(cur, epitope_id)
                break

        return render_template("base.jinja2", html=tsv2rdf.render(html))


@app.route('/epitope/')
def epitopes():
    with sqlite3.connect(sqlite, uri=True) as conn:
        conn.row_factory = dict_factory
        cur = conn.cursor()
        table = "epitope"
        cur.execute(f"SELECT count(*) AS count FROM {table}")
        row = cur.fetchone()
        count = row["count"]
        page = int(request.args.get("page", "1"))
        offset = (page - 1) * limit
        cur.execute(f"""SELECT epitope_id,
            e_object_desc AS epitope,
            e_object_mol_name AS antigen,
            e_object_organism_name AS organism
          FROM epitope
          ORDER BY epitope_id
          LIMIT {limit}
          OFFSET {offset}""")
        table = make_paged_table(cur.fetchall(), count, page)
        html = ["div", ["h2", "Epitopes"], table]
        return render_template("base.jinja2", html=tsv2rdf.render(html))


def make_epitope(cur, epitope_id):
    html = []
    cur.execute(f"SELECT * FROM epitope WHERE epitope_id = '{epitope_id}'")
    row = cur.fetchone()
    object_id = row.get("e_object_id")
    related_id = row.get("related_object_id")
    html.append(["h3", f"Epitope {epitope_id}"])
    html.append(make_kv(row))

    if object_id:
        cur.execute(f"SELECT * FROM object WHERE object_id = '{object_id}'")
        row = cur.fetchone()
        if row:
            html.append(["h3", f"Object {object_id}"])
            html.append(make_kv(row))

    if related_id:
        object_id = related_id
        cur.execute(f"SELECT * FROM object WHERE object_id = '{object_id}'")
        row = cur.fetchone()
        if row:
            html.append(["h3", f"Related Object {object_id}"])
            html.append(make_kv(row))

    return html


@app.route('/epitope/<epitope_id>')
def epitope(epitope_id):
    with sqlite3.connect(sqlite, uri=True) as conn:
        conn.row_factory = dict_factory
        cur = conn.cursor()
        html = ["div", ["h2", ["a", {"href": "./"}, "Epitopes"]]]
        html += make_epitope(cur, epitope_id)

        return render_template("base.jinja2", html=tsv2rdf.render(html))


# Proxy /sqlite-web to localhost 8080
SITE_NAME="http://localhost:8080/sqlite-web/"
@app.route('/sqlite-web/', defaults={"path": ""})
@app.route('/sqlite-web/<path:path>', methods=["GET", "POST"])
def proxy(path):
    excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    if request.method=='GET':
        resp = get(f'{SITE_NAME}{path}')
    elif request.method=='POST':
        resp = post(f'{SITE_NAME}{path}', request.form)
    headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]
    response = Response(resp.content, resp.status_code, headers)
    return response


@app.route('/<tree>')
def tree(tree):
    return redirect(root + tree + "/NCBITaxon:1")


@app.route('/<tree>/<term_id>')
def term(tree, term_id):
    return tsv2rdf.terms2rdfa(data, tree, [term_id])


if __name__ == '__main__':
    app.run(port=5006)
