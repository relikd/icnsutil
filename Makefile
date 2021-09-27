.PHONY: help test sys-icons-print sys-icons-test

help:
	@echo 'Available commands: test, sys-icons-print, sys-icons-test'

test:
	python3 tests/test_icnsutil.py

_listofsystemicns.txt:
	@echo 'Generate list of system icns files...'
	find /Applications -type f -name '*.icns' > _listofsystemicns.txt || echo
	find /Users -type f -name '*.icns' >> _listofsystemicns.txt || echo
	find /Library -type f -name '*.icns' >> _listofsystemicns.txt || echo
	find /System -not \( -path '/System/Volumes' -prune \) \
		-not \( -path '/System/Library/Templates' -prune \) \
		-type f -name '*.icns' >> _listofsystemicns.txt || echo 'Done.'

sys-icons-print: _listofsystemicns.txt
	@while read fname; do \
		./cli.py print "$${fname}"; \
	done < _listofsystemicns.txt

sys-icons-test: _listofsystemicns.txt
	@while read fname; do \
		./cli.py test -q "$${fname}"; \
	done < _listofsystemicns.txt
