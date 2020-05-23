#!/usr/bin/env python3

import argparse
import csv
import io
import os
import uuid
import zipfile

from collections import defaultdict
from datetime import date

oio = {
    "SynonymTypeProperty": "synonym_type_property",
    "hasAlternativeId": "has_alternative_id",
    "hasBroadSynonym": "has_broad_synonym",
    "hasDbXref": "database_cross_reference",
    "hasExactSynonym": "has_exact_synonym",
    "hasOBOFormatVersion": "has_obo_format_version",
    "hasOBONamespace": "has_obo_namespace",
    "hasRelatedSynonym": "has_related_synonym",
    "hasScope": "has_scope",
    "hasSynonymType": "has_synonym_type",
}

exact_synonym = "oio:hasExactSynonym"
related_synonym = "oio:hasRelatedSynonym"
broad_synonym = "oio:hasBroadSynonym"

predicates = {
    "acronym": broad_synonym,
    "anamorph": related_synonym,
    "blast name": related_synonym,
    "common name": exact_synonym,
    "equivalent name": exact_synonym,
    "genbank acronym": broad_synonym,
    "genbank anamorph": related_synonym,
    "genbank common name": exact_synonym,
    "genbank synonym": related_synonym,
    "in-part": related_synonym,
    "misnomer": related_synonym,
    "misspelling": related_synonym,
    "synonym": related_synonym,
    "scientific name": exact_synonym,
    "teleomorph": related_synonym,
}

ranks = [
    "class",
    "cohort",
    "family",
    "forma",
    "genus",
    "infraclass",
    "infraorder",
    "kingdom",
    "order",
    "parvorder",
    "phylum",
    "section",
    "series",
    "species group",
    "species subgroup",
    "species",
    "subclass",
    "subcohort",
    "subfamily",
    "subgenus",
    "subkingdom",
    "suborder",
    "subphylum",
    "subsection",
    "subspecies",
    "subtribe",
    "superclass",
    "superfamily",
    "superkingdom",
    "superorder",
    "superphylum",
    "tribe",
    "varietas",
]

nodes_fields = [
    "tax_id",  # node id in GenBank taxonomy database
    "parent_tax_id",  # parent node id in GenBank taxonomy database
    "rank",  # rank of this node (superkingdom, kingdom, ...)
    "embl_code",  # locus-name prefix; not unique
    "division_id",  # see division.dmp file
    "inherited_div_flag",  # (1 or 0) 1 if node inherits division from parent
    "genetic_code_id",  # see gencode.dmp file
    "inherited_GC_flag",  # (1 or 0) 1 if node inherits genetic code from parent
    "mitochondrial_genetic_code_id",  # see gencode.dmp file
    "inherited_MGC_flag",  # (1 or 0) 1 if node inherits mitochondrial gencode from parent
    "GenBank_hidden_flag",  # (1 or 0) 1 if name is suppressed in GenBank entry lineage
    "hidden_subtree_root_flag",  # (1 or 0) 1 if this subtree has no sequence data yet
    "comments",  # free-text comments and citations
]

def count_epitopes(object_path):
    epitope_counts = defaultdict(int)
    with open(object_path) as tsv:
        rows = csv.DictReader(tsv, delimiter="\t")
        for row in rows:
            if not row["epitope_id"]:
                continue
            tax_id = row["organism_id"] or row["organism2_id"] # or row["mol1_source_id"] or row["mol2_source_id"]
            if not tax_id:
                continue
            epitope_counts[tax_id] += 1
    return epitope_counts


def escape_literal(text):
    return text.replace('"', '\\"')


def label_to_id(text):
    return text.replace(" ", "_").replace("-", "_")


def convert_synonyms(tax_id, synonyms):
    """Given a tax_id and list of synonyms,
    return a Turtle string asserting triples and OWL annotations on them."""
    output = []
    for synonym, unique, name_class in synonyms:
        if name_class not in predicates:
            continue
        synonym = escape_literal(synonym)
        sc = f"NCBITaxon:{tax_id}"
        sb = uuid.uuid4()
        pc = predicates[name_class]
        oc = "ncbitaxon:" + label_to_id(name_class)
        output += [
            {"sc": sc, "pc": pc, "ol": synonym},
            {"sb": sb, "pc": "rdf:type", "oc": "owl:Axiom"},
            {"sb": sb, "pc": "owl:annotatedSource", "oc": sc},
            {"sb": sb, "pc": "owl:annotatedProperty", "oc": pc},
            {"sb": sb, "pc": "owl:annotatedTarget", "ol": synonym, "dc": "xsd:string"},
            {"sb": sb, "pc": "oio:hasSynonymType", "oc": oc}]
    return output


def convert_node(node, label, merged, synonyms, citations):
    """Given a node dictionary, a label string, and lists for merged, synonyms, and citations,
    return a Turtle string representing this tax_id."""
    tax_id = node["tax_id"]
    sc = f"NCBITaxon:{tax_id}"
    label = escape_literal(label)
    output = [
        {"sc": sc, "pc": "rdf:type", "oc": "owl:Class"},
        {"sc": sc, "pc": "rdfs:label", "ol": label, "dc": "xsd:string"},
        {"sc": sc, "pc": "iedb:browser-link", "oi": f"http://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id={tax_id}"},
    ]

    parent_tax_id = node["parent_tax_id"]
    if parent_tax_id and parent_tax_id != "" and parent_tax_id != tax_id:
        output.append({"sc": sc, "pc": "rdfs:subClassOf", "oc": f"NCBITaxon:{parent_tax_id}"})

    rank = node["rank"]
    if rank and rank != "" and rank != "no rank":
        if rank not in ranks:
            print(f"WARN Unrecognized rank '{rank}'")
        rank = label_to_id(rank)
        # WARN: This is a special case for backward compatibility
        if rank in ["species_group", "species_subgroup"]:
            output.append({"sc": sc, "pc": "ncbitaxon:has_rank", "oi": f"http://purl.obolibrary.org/obo/NCBITaxon#_{rank}"})
        else:
            output.append({"sc": sc, "pc": "ncbitaxon:has_rank", "oc": f"NCBITaxon:{rank}"})

    gc_id = node["genetic_code_id"]
    if gc_id:
        output.append({"sc": sc, "pc": "oio:hasDbXref", "ol": f"GC_ID:{gc_id}", "dc": "xsd:string"})

    for merge in merged:
        output.append({"sc": sc, "pc": "oio:hasAlternativeId", "ol": f"NCBITaxon:{merge}", "dc": "xsd:string"})

    for pubmed_id in citations:
        output.append({"sc": sc, "pc": "oio:hasDbXref", "ol": f"PMID:{pubmed_id}", "dc": "xsd:string"})

    output.append({"sc": sc, "pc": "oio:hasOBONamespace", "ol": "ncbi_taxonomy", "dc": "xsd:string"})

    output += convert_synonyms(tax_id, synonyms)
    for row in output:
        row["zn"] = sc

    return output


def split_line(line):
    """Split a line from a .dmp file"""
    return [x.strip() for x in line.split("	|")]


def get_ancestors(parents, leaf):
    ancestors = []
    node = leaf
    while node and node in parents:
        parent = parents[node]
        if node == parent:
            break
        ancestors.append(parent)
        node = parents[node]
    ancestors.reverse()
    return ancestors


def prune_poles(tree, node):
    children = tree[node]["children"]
    if len(children) > 1:
        child = children.pop()
        tree[node]["children"] = [child]
        prune_poles(tree, child)


def write_tree(tree, path):
    headers = ["id", "label", "parents", "children", "epitope_count", "epitope_sum"]
    with open(path, "w") as tsv:
        writer = csv.DictWriter(tsv, headers, delimiter="\t", lineterminator="\n", extrasaction='ignore')
        writer.writeheader()
        for row in tree.values():
            newrow = row.copy()
            newrow["parents"] = " ".join(f"NCBITaxon:{x}" for x in row["parents"])
            newrow["children"] = " ".join(f"NCBITaxon:{x}" for x in row["children"])
            writer.writerow(newrow)


def convert(taxdmp_path, outdir_path, weights=None):
    """Given the paths to the taxdmp.zip file and an output Turtle file,
    and an optional set of tax_id strings to extract,
    read from the taxdmp.zip file, collect annotations,
    convert nodes to Turtle strings,
    and write to the output file."""
    scientific_names = defaultdict(list)
    labels = {}
    synonyms = defaultdict(list)
    merged = defaultdict(list)
    citations = defaultdict(list)
    with zipfile.ZipFile(taxdmp_path) as taxdmp:
        parents = {}
        species = set()
        with taxdmp.open("nodes.dmp") as dmp:
            for line in io.TextIOWrapper(dmp):
                tax_id, parent, rank = split_line(line)[0:3]
                parents[tax_id] = parent
                if rank == "species":
                    species.add(tax_id)

        taxa = set()
        tree = {}
        esum = 0
        for tax_id, epitope_count in weights.items():
            esum += epitope_count
            if tax_id not in parents:
                continue
            tree[tax_id] = {
                "tax_id": tax_id,
                "id": f"NCBITaxon:{tax_id}",
                "epitope_count": epitope_count,
                "epitope_sum": epitope_count,
                "parents": {parents[tax_id]},
                "children": set(),
            }
        for active, epitope_count in weights.items():
            taxa.add(active)
            child = active
            ancestors = get_ancestors(parents, active)
            ancestors.reverse()
            for tax_id in ancestors:
                taxa.add(tax_id)
                if tax_id not in tree:
                    tree[tax_id] = {
                        "tax_id": tax_id,
                        "id": f"NCBITaxon:{tax_id}",
                        "epitope_count": 0,
                        "epitope_sum": 0,
                        "parents": {parents[tax_id]},
                        "children": set(),
                    }
                tree[tax_id]["epitope_sum"] += epitope_count
                tree[tax_id]["children"].add(child)
                child = tax_id

        del parents, species

        with taxdmp.open("names.dmp") as dmp:
            for line in io.TextIOWrapper(dmp):
                tax_id, name, unique, name_class, _ = split_line(line)
                if taxa and tax_id not in taxa:
                    continue
                if name_class == "scientific name":
                    labels[tax_id] = name
                    scientific_names[name].append([tax_id, unique])
                else:
                    synonyms[tax_id].append([name, unique, name_class])

        # use unique name only if there's a conflict
        for name, values in scientific_names.items():
            tax_ids = [x[0] for x in values]
            if len(tax_ids) > 1:
                uniques = [x[1] for x in values]
                if len(tax_ids) != len(set(uniques)):
                    print("WARN: Duplicate unique names", tax_ids, uniques)
                for tax_id, unique in values:
                    labels[tax_id] = unique
                    synonyms[tax_id].append([name, unique, "scientific name"])

        for row in tree.values():
            row["label"] = labels.get(row["tax_id"])
        write_tree(tree, os.path.join(outdir_path, "1_active.tsv"))

        prune_poles(tree, "1")
        write_tree(tree, os.path.join(outdir_path, "2_pruned.tsv"))

        #with taxdmp.open("merged.dmp") as dmp:
        #    for line in io.TextIOWrapper(dmp):
        #        old_tax_id, new_tax_id, _ = split_line(line)
        #        merged[new_tax_id].append(old_tax_id)

        #with taxdmp.open("citations.dmp") as dmp:
        #    for line in io.TextIOWrapper(dmp):
        #        (
        #            cit_id,
        #            cit_key,
        #            pubmed_id,
        #            medline_id,
        #            url,
        #            text,
        #            tax_id_list,
        #            _,
        #        ) = split_line(line)
        #        # WARN: the pubmed_id is always "0", we treat medline_id as pubmed_id
        #        if medline_id == "0":
        #            continue
        #        for tax_id in tax_id_list.split():
        #            if taxa and tax_id not in taxa:
        #                continue
        #            citations[tax_id].append(medline_id)

        output_path = os.path.join(outdir_path, "statements.tsv")
        headers = ["zn", "sc", "sb", "pc", "oi", "oc", "ob", "ol", "dc", "lt"]
        with open(output_path, "w") as tsv:
            writer = csv.DictWriter(tsv, headers, delimiter="\t", lineterminator="\n")
            writer.writeheader()

            with taxdmp.open("nodes.dmp") as dmp:
                for line in io.TextIOWrapper(dmp):
                    node = {}
                    fields = split_line(line)
                    for i in range(0, min(len(fields), len(nodes_fields))):
                        node[nodes_fields[i]] = fields[i]
                    tax_id = node["tax_id"]
                    if taxa and tax_id not in taxa:
                        continue
                    results = convert_node(
                        node,
                        labels[tax_id],
                        merged[tax_id],
                        synonyms[tax_id],
                        citations[tax_id],
                    )
                    writer.writerows(results)


def main():
    parser = argparse.ArgumentParser(
        description="Convert NCBI Taxonomy taxdmp.zip to Turtle format"
    )
    parser.add_argument("taxdmp", type=str, help="The taxdmp.zip file to read")
    parser.add_argument("object", type=str, help="The object table")
    parser.add_argument("outdir", type=str, help="The output directory")
    args = parser.parse_args()

    taxa = count_epitopes(args.object)
    return
    convert(args.taxdmp, args.outdir, taxa)


if __name__ == "__main__":
    main()
