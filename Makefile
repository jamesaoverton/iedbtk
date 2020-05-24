### General Tasks

.PHONY: usage
usage:
	@echo "Usage: make [task]"
	@echo "  all        run all tasks"
	@echo "  clean      delete temporary build files"
	@echo "  config     update configuration"
	@echo "  iedb       fetch IEDB data"
	@echo "  sot        rebuild Source of Truth"
	@echo "  serve      run a local server"
	@echo "  test       run automated tests"
	@echo "  lint       check code style"
	@echo "  format     automatically reformat code"

.PHONY: all
all: sot test


### GNU Make Configuration
#
# These are standard options to make Make sane:
# <http://clarkgrubb.com/makefile-style-guide#toc2>

MAKEFLAGS += --warn-undefined-variables
SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.DELETE_ON_ERROR:
.SUFFIXES:
.SECONDARY:

XLSX := xlsx2csv --delimiter tab --escape --ignoreempty
PYTHON_FILES := src tests


### Build and Clean

build/% cache/%:
	mkdir -p $@

.PHONY: clean
clean:
	rm -rf build


### CONFIG

build/sot/lji_sot.xlsx: | build/sot
	curl -L -o $@ "https://docs.google.com/spreadsheets/d/16M0RyUBEw_fW09x0U2X1vIXrek_dl2qMvqcOA7xI0WU/export?format=xlsx"

SOT_SHEETS := ncbi_taxa taxon_parents assays diseases
SOT_TSVS := $(foreach S,$(SOT_SHEETS),conf/$(S).tsv)
$(SOT_TSVS): build/sot/lji_sot.xlsx
	$(XLSX) -n $(basename $(notdir $@)) $< > $@

.PHONY: config
config: $(SOT_TSVS)


### IEDB
#
# Fetch data from IEDB

IEDB_TABLES := reference article
IEDB_TSVS := $(foreach X,$(IEDB_TABLES),cache/iedb/$(X).tsv)
$(IEDB_TSVS): src/iedbtk/fetch.py references.tsv | cache/iedb
	python3 $< IEDB $(basename $(notdir $@)) --references $(word 2,$^) > $@

build/iedb.sql: $(IEDB_TSVS)
	echo ".mode tabs" > $@
	$(foreach X,$^,echo ".import $(X) $(basename $(notdir $X))" >> $@;)

build/iedb.db: build/iedb.sql
	sqlite3 $@ < $<

.PHONY: iedb
iedb: build/iedb.db


### TREES

## Assay Tree

cache/sot/obi.owl: | cache/sot
	curl -LO "http://purl.obolibrary.org/obo/obi.owl"


## Organism Tree

cache/taxdmp.zip: | cache/sot
	curl -L -o $@ "https://ftp.ncbi.nih.gov/pub/taxonomy/taxdmp.zip"

# Remove pipes and escape quotes
TAX_SHEETS := nodes names citations merged delnodes
TAX_TSVS := $(foreach S,$(TAX_SHEETS),build/taxdmp/$(S).tsv)
$(TAX_TSVS): cache/taxdmp.zip | build/taxdmp
	unzip -p $< $(basename $(notdir $@)).dmp \
	| sed "s/	|//g"  \
	| sed 's/"/\\"/g' \
	> $@

build/taxdmp.db: src/iedbtk/taxdmp.sql $(TAX_TSVS)
	sqlite3 $@ < $<

build/trees.db: src/iedbtk/organism.sql build/taxdmp.db cache/weights.tsv
	sqlite3 $@ < $<

.PHONY: trees
trees: build/trees.db


### SERVE

.PHONY: serve
serve: build/iedb.db
	./run.sh $^


### TEST, LINT, FORMAT

.PHONY: test
test:
	#pytest tests
	rm -f build/trees.db
	make trees

.PHONY: lint
lint:
	flake8 --max-line-length 100 --ignore E203,W503 $(PYTHON_FILES)
	black --line-length 100 --quiet --check $(PYTHON_FILES)

.PHONY: format
format:
	black --line-length 100 $(PYTHON_FILES)

