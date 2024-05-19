TS_GEN_DATA = ./public/js/generateMetadata.ts
JS_GEN_DATA = ./public/js/generateMetadata.js
JS_RENAME_FILE = ./public/js/rename_files.js
JS_UPDATE_CONFIG = ./public/js/update_config.js
JS_SERVER = server.js

run:
	@echo "Running $(TS_GEN_DATA) TS_GEN_DATA generate JS file"
	tsc $(TS_GEN_DATA)
	@echo "Running $(JS_GEN_DATA) JS_GEN_DATA to create metada for coordinates"
	node $(JS_GEN_DATA)
	@echo "Running $(JS_RENAME_FILE) JS_RENAME_FILE to create the right file names to insert in R2"
	node $(JS_GEN_DATA)
	@echo "Running $(JS_UPDATE_CONFIG) JS_UPDATE_CONFIG to update config references"
	node $(JS_UPDATE_CONFIG)

server:
	@echo $(JS_SERVER) running server..
	node $(JS_SERVER)