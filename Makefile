build:
	rm -rf dist/* && python build.py --config config/ppi-codebook.json

tag: build
	./tag.sh

publish: tag
	git push origin gh-pages && git push --tags
