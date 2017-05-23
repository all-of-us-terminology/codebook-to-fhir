build:
	rm -rf dist/* && python build.py --config config/ppi-codebook.json

validate-prerelease:
	rm -rf dist/* && python build.py --config config/ppi-codebook-prerelease.json

tag: build
	./tag.sh

publish: tag
	git push origin gh-pages && git push --tags
