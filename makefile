SOURCE=src
TARGET=www

.PHONY = render clean

render:
	python -c "import sage.newdoc; sage.newdoc.Renderer('${SOURCE}', '${TARGET}').render()"

clean:
	$(RM) -r ${TARGET}
	find sage/newdoc -name "*.pyc" -delete

style:
	autopep8 -aaa -i --aggressive --max-line-length=120 `find sage/newdoc -name "*.py"`
