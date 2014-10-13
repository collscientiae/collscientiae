NAME=collscientiae

.PHONY = clean style test

test:
	nosetests -v -s \
        --with-coverage --with-doctest --cover-erase \
        --cover-package=${NAME}

clean:
	find ${NAME} -name "*.pyc" -delete

style:
	autopep8 -aaa -i --aggressive --max-line-length=120 `find ${NAME} -name "*.py"`

