#!/usr/binmenv python3

import argparse
import csv
import os

from collections import defaultdict
from copy import deepcopy


def curie2iri(prefixes, curie):
    for prefix, base in prefixes:
        if curie.startswith(prefix + ":"):
            return curie.replace(prefix + ":", base)
    raise Exception(f"No matching prefix for {curie}")


def curie2href(curie):
    return f"./{curie}".replace("#", "%23")


def render(element, depth=0):
    indent = "  " * depth
    if not isinstance(element, list):
        raise Exception(f"Element is not a list: {element}")
    if len(element) == 0:
        raise Exception(f"Element is an empty list")
    tag = element.pop(0)
    if not isinstance(tag, str):
        raise Exception(f"Tag '{tag}' is not a string in '{element}'")
    output = f"{indent}<{tag}"

    if len(element) > 0 and isinstance(element[0], dict):
        attrs = element.pop(0)
        if tag == "a" and "href" not in attrs and "resource" in attrs:
            attrs["href"] = curie2href(attrs["resource"])
        for key, value in attrs.items():
            if key in ["checked"]:
                if value:
                    output += f" {key}"
            else:
                output += f' {key}="{value}"'

    if tag in ["meta", "link"]:
        output += "/>"
        return output
    output += ">"
    spacing = ""
    if len(element) > 0:
        for child in element:
            if isinstance(child, str):
                output += child
            elif isinstance(child, list):
                try:
                    output += "\n" + render(child, depth + 1)
                    spacing = f"\n{indent}"
                except Exception as e:
                    raise Exception(f"Bad child in '{element}'", e)
            else:
                raise Exception(f"Bad type for child '{child}' in '{element}'")
    output += f"{spacing}</{tag}>"
    return output


def read_statements(data, path):
    name, ext = os.path.splitext(os.path.basename(path))
    stanzas = defaultdict(list)
    with open(path) as tsv:
        rows = csv.DictReader(tsv, delimiter="\t")
        for row in rows:
            stanzas[row["zn"]].append(row)
    data["stanzas"] = stanzas
    return data


def read_tree(data, path):
    name, ext = os.path.splitext(os.path.basename(path))
    tree = {}
    with open(path) as tsv:
        rows = csv.DictReader(tsv, delimiter="\t")
        for row in rows:
            row["parents"] = row["parents"].split()
            row["children"] = row["children"].split()
            tree[row["id"]] = row
    data[name] = tree
    data["trees"].append(name)
    return data


def readdir(path):
    data = {}

    prefixes_path = os.path.join(path, "prefixes.tsv")
    prefixes = []
    with open(prefixes_path) as tsv:
        rows = csv.reader(tsv, delimiter="\t")
        for row in rows:
            prefixes.append(row)
    data["manual_prefixes"] = prefixes.copy()
    prefixes.sort(key=lambda x: len(x[0]), reverse=True)
    data["prefixes"] = prefixes
    
    data["labels"] = {"rdfs:subClassOf": "subclass of",
              "rdf:type": "type",
              "rdfs:label": "label",
              "owl:Class": "Class",
              }
    data["trees"] = []

    for root, dirs, files in os.walk(path):
       for name in files:
           if name == "prefixes.tsv":
               continue
           elif name == "statements.tsv":
               read_statements(data, os.path.join(root, name))
           elif name.endswith(".tsv"):
               read_tree(data, os.path.join(root, name))

    return data


def tree_label(data, treename, s):
    node = data[treename][s]
    #return "{label} ({epitope_sum} {epitope_count})".format(**node)
    return node.get("label", s)


def row2o(data, row):
    predicate = row["predicate"]
    obj = row["object"]
    if isinstance(obj, str):
        if obj.startswith("<"):
            iri = obj[1:-1]
            return ["a", {"rel": predicate, "href": iri}, iri]
        elif obj.startswith("_:"):
            return ["span", {"property": predicate}, obj]
        else:
            return ["a",
                    {"rel": predicate, "resource": obj},
                    data["labels"].get(obj, obj)]
    # TODO: OWL expressions
    # TODO: other blank objects
    # TODO: datatypes
    # TODO: languages
    elif row["value"]:
        return ["span", {"property": predicate}, row["value"]]


def row2po(data, row):
    predicate = row["predicate"]
    P = data["labels"].get(predicate, predicate)
    p = ["a", {"href": curie2href(predicate)}, P]
    o = row2o(data, row)
    return [p, o]


def term2tree(data, treename, term_id):
    if treename not in data or term_id not in data[treename]:
        return ""

    tree = data[treename][term_id]
    child_labels = []
    for child in tree["children"]:
        child_labels.append([child, data["labels"].get(child, child)])
    child_labels.sort(key=lambda x: x[1].lower())

    max_children = 100
    children = []
    for child, label in child_labels:
        if not child in data[treename]:
            continue
        predicate = "rdfs:subClassOf"
        oc = child
        O = tree_label(data, treename, oc)
        o = ["a", {"rev": predicate, "resource": oc}, O]
        attrs = {}
        if len(children) > max_children:
            attrs["style"] = "display: none"
        children.append(["li", attrs, o])
        if len(children) == max_children:
            total = len(tree["children"])
            attrs = {"href": "javascript:show_children()"}
            children.append(["li", {"id": "more"}, ["a", attrs, f"Click to show all {total} ..."]])
    children = ["ul", {"id": "children"}] + children
    if len(children) == 0:
        children = ""

    hierarchy = ["ul", ["li", tree_label(data, treename, term_id), children]]
    indent = 0
    i = 0
    node = tree["parents"][0]
    if term_id != "NCBITaxon:1":
        while node and i < 100:
            i += 1
            predicate = "rdfs:subClassOf"
            oc = node
            O = tree_label(data, treename, node)
            o = ["a", {"rel": predicate, "resource": oc}, O]
            hierarchy = ["ul", ["li", o, hierarchy]]
            parents = data[treename][node]["parents"]
            if len(parents) == 0:
                break
            parent = parents[0]
            if node == parent:
                break
            node = parent

    hierarchy.insert(1, {"id": "hierarchy", "class": "col-md"})
    return hierarchy


def term2rdfa(cur, prefixes, treename, stanza, term_id):
    if len(stanza) == 0:
        return set(), "Not found"
    curies = set()
    tree = {}
    cur.execute(f"""
      WITH RECURSIVE ancestors(parent, child) AS (
        VALUES ('{term_id}', NULL)
        UNION
        SELECT object AS parent, subject AS child
        FROM statements
        WHERE predicate = 'rdfs:subClassOf'
          AND object = '{term_id}'
        UNION
        SELECT object AS parent, subject AS child
        FROM statements, ancestors
        WHERE ancestors.parent = statements.stanza
          AND statements.predicate = 'rdfs:subClassOf'
          AND statements.object NOT LIKE '_:%'
      )
      SELECT * FROM ancestors""")
    for row in cur.fetchall():
        #print(row)
        parent = row["parent"]
        if not parent:
            continue
        curies.add(parent)
        if parent not in tree:
            tree[parent] = {
                "parents": [],
                "children": [],
            }
        child = row["child"]
        if not child:
            continue
        curies.add(child)
        if child not in tree:
            tree[child] = {
                "parents": [],
                "children": [],
            }
        tree[parent]["children"].append(child)
        tree[child]["parents"].append(parent)
    print("TREE ", len(tree.keys()))
    data = {"labels": {}}
    data[treename] = tree

    stanza.sort(key=lambda x: x["predicate"])

    for row in stanza:
        curies.add(row.get("subject"))
        curies.add(row.get("predicate"))
        curies.add(row.get("object"))
    curies.discard('')
    curies.discard(None)
    ps = set()
    for curie in curies:
        if not isinstance(curie, str) or len(curie) == 0 or curie[0] in ("_", "<"):
            continue
        prefix, local = curie.split(":")
        ps.add(prefix)

    labels = {}
    ids = "', '".join(curies)
    cur.execute(f"""SELECT subject, value
      FROM statements
      WHERE stanza IN ('{ids}')
        AND predicate = 'rdfs:label'
        AND value IS NOT NULL""")
    for row in cur:
        labels[row["subject"]] = row["value"]
    data["labels"] = labels
    for key in tree.keys():
        if key in labels:
            tree[key]["label"] = labels[key]

    label = term_id
    label_row = None
    for row in stanza:
        predicate = row["predicate"]
        if predicate == "rdfs:label":
            label_row = row
            label = label_row["value"]
            break

    annotation_bnodes = set()
    for row in stanza:
        if row["predicate"] == "rdf:type" and row["object"] == "owl:Axiom":
            annotation_bnodes.add(row["subject"])
    annotations = {}
    for row in stanza:
        subject = row["subject"]
        if subject not in annotation_bnodes:
            continue
        if subject not in annotations:
            annotations[subject] = {
                    "row": {"stanza": row["stanza"]},
                    "rows": []
                    }
        predicate = row["predicate"]
        if predicate == "rdf:type":
            continue
        elif predicate == "owl:annotatedSource":
            annotations[subject]["row"]["subject"] = row["object"]
            annotations[subject]["source"] = row
        elif predicate == "owl:annotatedProperty":
            annotations[subject]["row"]["predicate"] = row["object"]
            annotations[subject]["property"] = row
        elif predicate == "owl:annotatedTarget":
            annotations[subject]["row"]["object"] = row["object"]
            annotations[subject]["row"]["value"] = row["value"]
            annotations[subject]["row"]["datatype"] = row["datatype"]
            annotations[subject]["row"]["language"] = row["language"]
            annotations[subject]["target"] = row
        else:
            annotations[subject]["rows"].append(row)

    subject = row["subject"]
    si = curie2iri(prefixes, subject)
    S = label

    items = ["ul", {"id": "annotations", "class": "col-md"}]
    s2 = defaultdict(list)
    for row in stanza:
        if row["subject"] == term_id:
            s2[row["predicate"]].append(row)
    pcs = list(s2.keys())
    pcs.sort()
    for predicate in pcs:
        p = ["a", {"href": curie2href(predicate)}, labels.get(predicate, predicate)]
        os = []
        for row in s2[predicate]:
            if row == label_row:
                continue
            o = ["li", row2o(data, row)]
            for key, ann in annotations.items():
                if row != ann["row"]:
                    continue
                ul = ["ul"]
                for a in ann["rows"]:
                    ul.append(["li"] + row2po(data, a))
                o.append(
                   ["small",
                    {"resource": key},
                    ["div",
                     {"hidden": "true"},
                     row2o(data, ann["source"]),
                     row2o(data, ann["property"]),
                     row2o(data, ann["target"])],
                    ul])
                break
            os.append(o)
        items.append(["li", p, ["ul"] + os])

    hierarchy = term2tree(data, treename, term_id)
    h2 = "" # term2tree(data, treename, term_id)

    term = ["div",
            {"resource": subject},
            ["h2", S],
            ["a", {"href": si}, si],
            ["div",
             {"class": "row"},
             hierarchy,
             h2,
             items]]
    return ps, term


def terms2rdfa(cur, treename, term_ids):
    cur.execute(f"SELECT * FROM prefix ORDER BY length(base) DESC")
    all_prefixes = [(x["prefix"], x["base"]) for x in cur.fetchall()]
    ps = set()
    terms = []
    for term_id in term_ids:
        cur.execute(f"SELECT * FROM statements WHERE stanza = '{term_id}'")
        stanza = cur.fetchall()
        p, t = term2rdfa(cur, all_prefixes, treename, stanza, term_id)
        ps.update(p)
        terms.append(t)

    prefixes = []
    #for prefix, base in data["manual_prefixes"]:
    #    if prefix in ps:
    #        prefixes.append(f"  {prefix}: {base}")
    prefixes = "\n" + "\n".join(prefixes)

    data = {"labels": {}}

    head = ["head",
             ["meta", {"charset": "utf-8"}],
             ["meta",
              {"name": "viewport",
               "content": "width=device-width, initial-scale=1, shrink-to-fit=no"}],
             ["link",
              {"rel": "stylesheet",
               "href": "https://stackpath.bootstrapcdn.com/bootstrap/4.5.0/css/bootstrap.min.css",
               "integrity": "sha384-9aIt2nRpC12Uk9gS9baDl411NQApFmC26EwAOH8WgZl5MYYxFfc+NcPb1dKGj7Sk",
               "crossorigin": "anonymous"}],
              ["link",
               {"rel": "stylesheet", "href": "../style.css"}],
              ["title", data["labels"].get(term_ids[0], "Term")]
             ]
    body = ["body",
            {"class": "container"},
            ["a", {"href": "../.."}, "Home"],
            " > ",
            ["a", {"href": ".."}, "Browser"],
            " > ",
            treename
            ] + terms
    body.append(["script",
        {"src": "https://code.jquery.com/jquery-3.5.1.min.js",
         "integrity": "sha256-9/aliU8dGd2tb6OSsuzixeV4y/faTqgFtohetphbbj0=",
         "crossorigin": "anonymous"}])
    body.append(["script", {"type": "text/javascript"}, """function show_children() {
        hidden = $('#children li:hidden').slice(0, 100);
        if (hidden.length > 1) {
            hidden.show();
            setTimeout(show_children, 100);
        } else {
            console.log("DONE");
        }
        $('#more').hide();
    }"""])
    html = ["html",
            {"prefixes": prefixes},
            head,
            body
        ]
    output = "<!doctype html>\n" + render(html)
    #escaped = output.replace("<","&lt;").replace(">","&gt;")
    #output += f"<pre><code>{escaped}</code></pre>"
    return output


def tsv2rdf(prefixes_path, input_path, ids, output_format, output_path):
    return


def test_tsv2rdf():
    pass


def main():
    parser = argparse.ArgumentParser(description="Convert an RDF file to TSV")
    parser.add_argument("prefixes", type=str, help="The prefixes TSV file")
    parser.add_argument("input", type=str, help="The input TSV file")
    parser.add_argument("ids", type=str, nargs="+", help="The term IDs")
    parser.add_argument("--format", type=str, default="RDFa", help="The output format")
    parser.add_argument("output", type=str, help="The output file")
    args = parser.parse_args()

    tsv2rdf(args.prefixes, args.input, args.ids, args.format, args.output)


if __name__ == "__main__":
    main()
