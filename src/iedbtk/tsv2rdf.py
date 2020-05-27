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
    return "{label} ({epitope_sum} {epitope_count})".format(**node)


def row2o(data, row):
    pc = row["pc"]
    if row["oc"]:
        oc = row["oc"]
        return ["a",
                {"rel": pc, "resource": oc},
                data["labels"].get(oc, oc)]
    elif row["oi"]:
        oi = row["oi"]
        return ["a", {"rel": pc, "href": oi}, oi]
    elif row["ob"]:
        ob = row["ob"]
        return ["span", {"property": pc}, ob]
    # TODO: OWL expressions
    # TODO: other blank objects
    # TODO: datatypes
    # TODO: languages
    elif row["ol"]:
        ol = row["ol"]
        return ["span", {"property": pc}, ol]


def row2po(data, row):
    pc = row["pc"]
    P = data["labels"].get(pc, pc)
    p = ["a", {"href": curie2href(pc)}, P]
    o = row2o(data, row)
    return [p, o]

def term2tree(data, treename, term_id):
    tree = data[treename][term_id]

    children = []
    for child in tree["children"]:
        if not child in data[treename]:
            continue
        pc = "rdfs:subClassOf"
        oc = child
        O = tree_label(data, treename, oc)
        o = ["a", {"rev": pc, "resource": oc}, O]
        children.append(["li", o])
    children.sort(key=lambda x: x[1][2])
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
            pc = "rdfs:subClassOf"
            oc = node
            O = tree_label(data, treename, node)
            o = ["a", {"rel": pc, "resource": oc}, O]
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


def term2rdfa(data, treename, term_id):
    if not term_id in data["stanzas"]:
        return set(), "Not found"
    stanza = data["stanzas"][term_id]
    if len(stanza) == 0:
        return set(), "Not found"
    tree = data[treename][term_id]

    stanza.sort(key=lambda x: x["pc"])

    curies = set()
    curies.update(tree["parents"])
    curies.update(tree["children"])
    for row in stanza:
        curies.add(row.get("sc"))
        curies.add(row.get("pc"))
        curies.add(row.get("oc"))
    curies.discard('')
    ps = set()
    for curie in curies:
        prefix, local = curie.split(":")
        ps.add(prefix)

    label = term_id
    label_row = None
    for row in stanza:
        pc = row["pc"]
        if pc == "rdfs:label":
            label_row = row
            label = label_row["ol"]
            break

    annotation_bnodes = set()
    for row in stanza:
        if row["pc"] == "rdf:type" and row["oc"] == "owl:Axiom":
            annotation_bnodes.add(row["sb"])
    annotations = {}
    for row in stanza:
        sb = row["sb"]
        if sb not in annotation_bnodes:
            continue
        if sb not in annotations:
            annotations[sb] = {
                    "row": {"zn": row["zn"], "sc":"", "sb":""},
                    "rows": []
                    }
        pc = row["pc"]
        if pc == "rdf:type":
            continue
        elif pc == "owl:annotatedSource":
            if row["oc"]:
                annotations[sb]["row"]["sc"] = row["oc"]
            elif row["ob"]:
                annotations[sb]["row"]["sb"] = row["ob"]
            annotations[sb]["source"] = row
        elif pc == "owl:annotatedProperty":
            annotations[sb]["row"]["pc"] = row["oc"]
            annotations[sb]["property"] = row
        elif pc == "owl:annotatedTarget":
            annotations[sb]["row"]["oi"] = row["oi"]
            annotations[sb]["row"]["oc"] = row["oc"]
            annotations[sb]["row"]["ob"] = row["ob"]
            annotations[sb]["row"]["ol"] = row["ol"]
            annotations[sb]["row"]["dc"] = row["dc"]
            annotations[sb]["row"]["lt"] = row["lt"]
            annotations[sb]["target"] = row
        else:
            annotations[sb]["rows"].append(row)

    sc = row["sc"]
    si = curie2iri(data["prefixes"], sc)
    S = label

    items = ["ul", {"id": "annotations", "class": "col-md"}]
    s2 = defaultdict(list)
    for row in stanza:
        if row["sc"] == term_id:
            s2[row["pc"]].append(row)
    pcs = list(s2.keys())
    pcs.sort()
    for pc in pcs:
        p = ["a", {"href": curie2href(pc)}, data["labels"].get(pc, pc)]
        os = []
        for row in s2[pc]:
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

    hierarchy = term2tree(data, "1_active", term_id)
    h2 = term2tree(data, treename, term_id)

    term = ["div",
            {"resource": sc},
            ["h2", S],
            ["a", {"href": si}, si],
            ["div",
             {"class": "row"},
             hierarchy,
             h2,
             items]]
    return ps, term


def terms2rdfa(data, treename, term_ids):
    ps = set()
    terms = []
    for term_id in term_ids:
        p, t = term2rdfa(data, treename, term_id)
        ps.update(p)
        terms.append(t)

    prefixes = []
    for prefix, base in data["manual_prefixes"]:
        if prefix in ps:
            prefixes.append(f"  {prefix}: {base}")
    prefixes = "\n" + "\n".join(prefixes)

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
