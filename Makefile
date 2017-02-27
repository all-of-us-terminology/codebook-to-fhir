build:
	python build.py --config config/ppi-codebook.json --version $(VERSION)

tag: build
	./tag.sh $(VERSION)

publish: tag
	git push origin gh-pages
