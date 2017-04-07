## Setup

    pip install click
    git clone git@github.com:all-of-us-terminology/codebook-to-fhir.git
    cd codebook-to-fhir
    
    # ensure we have a tracking branch
    git checkout gh-pages
    git checkout master

## Build locally

`   git checkout gh-pages && git pull && git checkout master`.
    make build
    cat dist/CodeSystem/ppi.issues.json

## Publish

    make publish
