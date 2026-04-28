.PHONY: install test dev clean

dev:
	pip install -e '.[dev]'

test:
	pytest

install:
	install -d $(DESTDIR)/usr/local/bin $(DESTDIR)/usr/local/share/call-cleaner
	install -m 755 bin/cleaner $(DESTDIR)/usr/local/bin/cleaner
	install -m 755 share/wrapper.sh $(DESTDIR)/usr/local/share/call-cleaner/wrapper.sh
	install -m 755 share/wrapper-purge.sh $(DESTDIR)/usr/local/share/call-cleaner/wrapper-purge.sh
	pip install --no-deps --target $(DESTDIR)/usr/local/lib/call-cleaner .

clean:
	rm -rf build dist *.egg-info .pytest_cache
	find . -name __pycache__ -type d -exec rm -rf {} +
