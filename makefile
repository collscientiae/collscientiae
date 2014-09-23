.PHONY = clean style

clean:
	find sage/newdoc -name "*.pyc" -delete

style:
	autopep8 -aaa -i --aggressive --max-line-length=120 `find sage/newdoc -name "*.py"`
