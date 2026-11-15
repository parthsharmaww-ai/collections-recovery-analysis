# End-to-end build.   make all RAW=/path/to/csvs   (default RAW=data/raw)
RAW ?= data/raw

.PHONY: all pipeline notebook dashboard memo diagram clean

all: pipeline notebook dashboard memo diagram

pipeline:            ## raw CSVs -> golden dataset + DQ + analysis tables (fails on CRITICAL DQ)
	python pipeline/run_pipeline.py --raw $(RAW)

notebook:            ## regenerate + execute the analysis notebook (also writes decision_summary.json)
	python notebooks/build_notebook.py
	cd notebooks && COLLECTIONS_RAW_DIR=$(abspath $(RAW)) jupyter nbconvert --to notebook --execute --inplace \
	    --ExecutePreprocessor.timeout=900 01_collections_analysis.ipynb
	cd notebooks && jupyter nbconvert --to html 01_collections_analysis.ipynb

dashboard:           ## one-screen executive dashboard (HTML) + refreshed data for the Tableau workbook
	python dashboard/build_dashboard.py
	python dashboard/tableau/build_tableau_data.py

memo:                ## 2-page executive memo (Markdown + PDF; PDF needs headless Chrome)
	python reports/build_memo.py

diagram:             ## architecture diagram (needs graphviz)
	dot -Tsvg docs/architecture.dot -o docs/architecture.svg
	dot -Tpng -Gdpi=150 docs/architecture.dot -o docs/architecture.png

clean:
	rm -rf output
