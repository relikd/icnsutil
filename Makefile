.PHONY: help
help:
	@echo 'commands:'
	@echo '  install, uninstall, test, dist, sys-icons-print, sys-icons-test'

.PHONY: install
install:
	[ -z "$${VIRTUAL_ENV}" ] \
	&& python3 -m pip install -e . --user \
	|| python3 -m pip install -e .

.PHONY: uninstall
uninstall:
	python3 -m pip uninstall icnsutil
	rm -rf ./*.egg-info/
	-rm -i "$$(which icnsutil)"

.PHONY: test
test:
	@echo 'Test lib...'
	@python3 tests/test_icnsutil.py
	@echo
	@echo 'Test CLI...'
	@python3 tests/test_cli.py

dist-env:
	@echo Creating virtual environment...
	@python3 -m venv 'dist-env'
	@source dist-env/bin/activate && pip install twine

.PHONY: dist
dist: dist-env
	[ -z "$${VIRTUAL_ENV}" ]  # you can not do this inside a virtual environment.
	rm -rf dist
	@echo Building...
	python3 setup.py sdist bdist_wheel
	@echo
	rm -rf ./*.egg-info/ ./build/ MANIFEST
	@echo Publishing...
	@echo "\033[0;31mEnter your PyPI token:\033[0m"
	@source dist-env/bin/activate && export TWINE_USERNAME='__token__' && twine upload dist/*

_icns_list.txt:
	@echo 'Generate list of system icns files...'
	-find /Applications -type f -name '*.icns' > _icns_list.txt
	-find /Users -type f -name '*.icns' >> _icns_list.txt
	-find /Library -type f -name '*.icns' >> _icns_list.txt
	-find /System -not \( -path '/System/Volumes' -prune \) \
		-not \( -path '/System/Library/Templates' -prune \) \
		-type f -name '*.icns' >> _icns_list.txt
	@echo 'Done.'

.PHONY: sys-icons-print
sys-icons-print: _icns_list.txt
	@cat _icns_list.txt | python3 -m icnsutil print -

.PHONY: sys-icons-test
sys-icons-test: _icns_list.txt
	@cat _icns_list.txt | python3 -m icnsutil test -q -
