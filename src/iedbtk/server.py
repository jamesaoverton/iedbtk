#!/usr/bin/env python3
import math
import sqlite3
import subprocess

from flask import Flask, request, redirect, Response, render_template
from requests import get, post
from urllib.parse import urlencode
import tsv2rdf

#root = "/browse/"
root = "/"
data = tsv2rdf.readdir("data2")
sqlite = "file:build/iedb.db?mode=ro"
app = Flask(__name__, instance_relative_config=True)

limit = 25

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
            ["p", ["a", {"href": "/search/"}, "Search"]],
            #["p", ["a", {"href": "/sqlite-web/"}, "SQL Browser"]]
            ]
    return render_template("base.jinja2", html=tsv2rdf.render(html))

links = {
    "reference_id": "http://iedb.org/reference/",
    "assay_id": "http://iedb.org/assay/",
    "epitope_id": "http://iedb.org/epitope/",
    "structure_id": "http://iedb.org/epitope/",
    "pubmed_id": "https://pubmed.ncbi.nlm.nih.gov/",
}

def make_page(args, page, string):
    args = args.copy()
    cls = "page-item"
    if args["page"] == page:
        cls += " disabled"
    args["page"] = page
    return ["li",
            {"class": cls},
            ["a",
             {"class": "page-link", "href": "?" + urlencode(args)},
             string]]


def make_paged_table(rows, count, args):
    page = int(args.get("page", "1"))
    last = math.ceil(count/limit)
    args["page"] = page
    html = ["div"]
    nav = ["ul", {"class": "pagination justify-content-center", "style": "margin-top: 1em"}]

    nav.append(make_page(args, 1, "first"))
    nav.append(make_page(args, max(1, page - 1), "prev"))

    js = f"javascript:jump({page})"
    nav.append(["li", {"class": "page-item"}, ["a", {"class": "page-link", "href": js}, f"page {page} of {last}"]])

    nav.append(make_page(args, min(last, page + 1), "next"))
    nav.append(make_page(args, last, "last"))

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
            value = str(value)
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

counts = {}

def my_count(cur, args):
    result = {
        "search": {"title": "Search"},
        "epitope": {"title": "Epitopes", "count": 1},
        "antigen": {"title": "Antigens", "count": 2},
        "assay": {"title": "Assays", "count": 3},
        "receptor": {"title": "Receptor", "count": 4},
        "reference": {"title": "References", "count": 5},
    }

    conditions = []
    if "sequence" in args and args["sequence"]:
        conditions.append(f"linear_sequence = '{args['sequence']}'")
    if conditions:
        conditions = "WHERE " + " AND ".join(conditions)
    else:
        conditions = ""
    result["search"]["conditions"] = conditions

    query = f"""SELECT
        count(distinct structure_id) AS epitope_count,
        count(distinct source_antigen_id) AS antigen_count,
        count(distinct assay_id) AS assay_count,
        count(distinct reference_id) AS reference_count
      FROM search {conditions}"""

    # Cache the counts
    if query in counts:
        return counts[query]

    cur.execute(query)
    row = cur.fetchone()
    result["epitope"]["count"] = row["epitope_count"]
    result["antigen"]["count"] = row["antigen_count"]
    result["assay"]["count"] = row["assay_count"]
    result["reference"]["count"] = row["reference_count"]
    counts[query] = result
    return result


@app.route('/search/')
def search():
    with sqlite3.connect(sqlite, uri=True) as conn:
        conn.row_factory = dict_factory
        cur = conn.cursor()
        html = ["div", ["h2", "Search"]]
        nav = ["ul", {"class": "nav nav-tabs justify-content-center", "style": "margin-bottom: 1em"}]
        tab = request.args.get("tab", "search")
        args = request.args.copy()
        args["page"] = 1
        result = my_count(cur, request.args)
        conditions = result["search"]["conditions"]
        for table, values in result.items():
            cls = "nav-link"
            if tab == table:
                cls += " active"
            args["tab"] = table
            title = values["title"]
            if "count" in values:
                title += f" ({values['count']})"
            nav.append(
               ["li",
                {"class": "nav-item"}, 
                ["a",
                 {"class": cls, "href": "?" + urlencode(args)},
                 title]])
        html.append(nav)

        args = request.args.copy()
        if tab == "search":
            form = ["form",
                    {"id": "search-form"},
                    ["p", "structure type list"],
                    ["p",
                     ["label", {"for": "sequence"}, "Epitope linear sequence"],
                     ["input", {"id": "sequence", "name": "sequence", "type": "text", "placeholder": "SIINFEKL", "value": request.args.get("sequence", "")}]],
                    ["p", "non-peptidic epitope finder"],
                    ["p", "organism finder"],
                    ["p", "antigen finder"],
                    ["p", "mhc finder"],
                    ["p", "host finder"],
                    ["p", "disease finder"],
                    ["p", "qualitative measure"],
                    ["p",
                     ["a", {"href": "/search/"}, "Clear"],
                     ["input", {"type": "submit", "value": "Search"}]]]
            html.append(form)

        elif tab == "epitope":
            table = "epitope"
            values = result[table]
            count = values["count"]
            page = int(request.args.get("page", "1"))
            offset = (page - 1) * limit
            cur.execute(f"""SELECT
                structure_id,
                description,
                source_antigen_label,
                source_organism_label,
                count(distinct assay_id) AS assays,
                count(distinct reference_id) AS "references"
              FROM search {conditions}
              GROUP BY structure_id
              LIMIT {limit}
              OFFSET {offset}""")
            html.append(make_paged_table(cur.fetchall(), count, dict(request.args)))

        elif tab == "antigen":
            table = "antigen"
            values = result[table]
            count = values["count"]
            page = int(request.args.get("page", "1"))
            offset = (page - 1) * limit
            cur.execute(f"""SELECT
                source_antigen_label,
                source_antigen_source_organism_label,
                count(distinct structure_id) AS epitopes,
                count(distinct assay_id) AS assays,
                count(distinct reference_id) AS "references"
              FROM search {conditions}
              GROUP BY source_antigen_id
              LIMIT {limit}
              OFFSET {offset}""")
            html.append(make_paged_table(cur.fetchall(), count, dict(request.args)))

        elif tab == "assay":
            table = "assay"
            values = result[table]
            count = values["count"]
            page = int(request.args.get("page", "1"))
            offset = (page - 1) * limit
            cur.execute(f"""SELECT DISTINCT
                assay_id,
                reference_id,
                assay_type_id
              FROM search {conditions}
              LIMIT {limit}
              OFFSET {offset}""")
            html.append(make_paged_table(cur.fetchall(), count, dict(request.args)))

        elif tab == "reference":
            table = "reference"
            values = result[table]
            count = values["count"]
            page = int(request.args.get("page", "1"))
            offset = (page - 1) * limit
            cur.execute(f"""SELECT DISTINCT
                reference_id,
                pubmed_id,
                reference_author,
                reference_title,
                reference_date
              FROM search {conditions}
              LIMIT {limit}
              OFFSET {offset}""")
            html.append(make_paged_table(cur.fetchall(), count, dict(request.args)))

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
    app.run(port=5005)
