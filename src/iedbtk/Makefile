.PHONY: all
all: ncbitaxon.owl ncbitaxon.obo

.PHONY: clean
clean:
	rm -rf build

build build/clean:
	mkdir -p $@

build/taxdmp.zip: | build
	curl -L -o $@ https://ftp.ncbi.nih.gov/pub/taxonomy/taxdmp.zip

build/taxdmp: build/taxdmp.zip | build
	unzip $< -d $@

# Remove pipes and escape quotes
build/%.tsv: build/taxdmp/%.dmp | build/clean
	sed "s/	|//g" $< | sed 's/"/\\"/g' > $@

build/taxdmp.db: import.sql build/nodes.tsv build/merged.tsv build/delnodes.tsv build/names.tsv build/citations.tsv
	sqlite3 $@ < $<

.PRECIOUS: ncbitaxon.owl
ncbitaxon.owl: src/ncbitaxon.py build/taxdmp.zip
	python3 $^ $@

.PRECIOUS: ncbitaxon.obo
ncbitaxon.obo: src/ncbitaxon.py build/taxdmp.zip
	python3 $^ $@


.PHONY: test
test:
	\time -f "%es %P%% %MKB" sqlite3 build/taxdmp.db < ../tree.sql
