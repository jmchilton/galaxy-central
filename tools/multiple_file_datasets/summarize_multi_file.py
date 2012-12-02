from optparse import OptionParser


def main():
    parser = OptionParser()
    parser.add_option("--report")
    parser.add_option("--input_file", action="append", default=[])
    parser.add_option("--input_name", action="append", default=[])
    parser.add_option("--input_ext", action="append", default=[])

    (options, _) = parser.parse_args()

    with(open(options.report, "w")) as f:
        for i, input_file in enumerate(options.input_file):
            f.write("-------------------\n")
            f.write(">Name: %s\n" % options.input_name[i])
            f.write(">Type: %s\n" % options.input_ext[i])
            f.write("%s\n\n" % open(input_file, "r").read())


if __name__ == "__main__":
    main()
