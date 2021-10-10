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
	python3 tests/test_icnsutil.py

.PHONY: dist
dist:
	@python3 setup.py sdist --formats=tar bdist_wheel \
	|| echo '-> you can not do this inside a virtual environment.'
	@echo
	rm -rf ./*.egg-info/ ./build/ MANIFEST

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
