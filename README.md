# Collectio Scientiam - Collection of Knowledge

This is an experimental new way to create a documentation.

## Objectives

- several unsorted piles of source documents are the basis for the entire documentation
- produced files are entirely static and hence no need for a dynamic web-server
- modularity with namespaces
- easy to edit for collaborators
- three-way distinction:
   - **Code**: core processing, processes an input directory with a `config.yaml` file
     into an empty output directory.
   - **Data**: input sources for the documentation are collected in a directory.
   - **Structure**: a special directory in the input data contains the blueprints for
     the output document (currently, only html templating)
- support for markdown with extensions:
  - knowls: transclusions for parts of documents
  - mathjax


## License

[Apache 2.0](http://www.apache.org/licenses/LICENSE-2.0)