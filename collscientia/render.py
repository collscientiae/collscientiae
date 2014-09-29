from os.path import abspath, normpath, isdir, join
from os import makedirs
from .models import Document
import codecs


class OutputRenderer(object):
    def __init__(self, log, db, targ):
        self.log = log
        self.db = db
        self.targ = targ

    def output(self):
        self.log.info("rendering into %s" % self.targ)
        self.output_index()
        self.output_documents()
        self.output_knowls()
        self.output_hashtags()

    def output_index(self):
        with open(join(self.targ, "index.html"), "w") as out:
            out.write("<h1>Modules</h1><ul>")
            for ns in self.db.docs.keys():
                out.write("<li><a href='{0}/index.html'>{0}</a></li>".format(ns))
            out.write("</ul><br><br>")
            out.write("<a href='hashtag/index.html'>list of all hashtags</a>")

    def output_knowls(self):
        for ns, docs in self.db.docs.iteritems():
            knowl_dir = join(self.targ, ns, "_knowl")
            assert not isdir(knowl_dir)
            makedirs(knowl_dir)
            for key, doc in docs.iteritems():
                out_fn = join(knowl_dir, '{}.{}'.format(doc.docid, "html"))
                with codecs.open(out_fn, "w", "utf8") as out:
                    out.write("knowl: %s" % doc.docid)

    def output_documents(self):
        for ns, docs in self.db.docs.iteritems():
            doc_dir = join(self.targ, ns)
            makedirs(doc_dir)

            with codecs.open(join(doc_dir, "index.html"), "w", "utf8") as out:
                out.write("""<a href="../index.html">up</a> |
                <a href="_knowl/">knowls</a>
                <h1>{0}</h1>
                <br>
                <ul>""".format(ns))
                for key in docs.keys():
                    out.write("<li><a href='{0}.html'>{0}</a></li>".format(key))
                out.write("<ul>")

            for key, doc in docs.iteritems():
                assert isinstance(doc, Document)
                out_fn = join(doc_dir, '{}.{}'.format(doc.docid, "html"))
                self.log.debug("  + %s" % out_fn)
                with codecs.open(out_fn, "w", "utf8") as out:
                    out.write(u"""<a href="../index.html">up</a> |
                    <a href="index.html">index</a>
                    <br>
                    <h1>{0.title}</h1>
                    <div><i>Abstract:</i>{0.abstract}</div>
                    <h2>Content:</h2>
                    {0.output}
                    """.format(doc))

    def output_hashtags(self):
        hashtag_dir = join(self.targ, "hashtag")
        makedirs(hashtag_dir)
        hashtags = sorted(self.db.hashtags.iteritems(),
                          key=lambda _: _[0])

        with open(join(hashtag_dir, "index.html"), "w") as out:
            out.write("""<a href="../index.html">up</a>
            <h1>Hashtags</h1>""")
            out.write("<ul>")
            for h in hashtags:
                link = "<li><a href='{0}.html'>#{0}</a></li>\n".format(h[0])
                out.write(link)
            out.write("</ul>")

        for hashtag, docs in hashtags:
            out_fn = join(hashtag_dir, '{}.{}'.format(hashtag, "html"))
            self.log.debug("  # %s" % out_fn)
            with open(out_fn, "w") as out:
                out.write("""<a href="../index.html">up</a> |
                            <a href="index.html">index</a>
                            <br>""")
                out.write("<ul>")
                for d in docs:
                    link = "<li><a href='../{0.namespace}/{0.docid}.html'>{0.docid}</a></li>" \
                        .format(d)
                    out.write(link)
                out.write("</ul>")
