import os
import re
import shutil
import sys


def main():
    extra_files_directory = sys.argv[1]
    multi_ext = sys.argv[2]
    db_key = sys.argv[3]
    report = sys.argv[4]
    report_id = sys.argv[5]
    new_files_directory = sys.argv[6]

    ext = multi_ext[len("m:"):]

    extra_file_names = sorted(os.listdir(extra_files_directory))
    datasets_created = []
    for name in extra_file_names:
        source = os.path.join(extra_files_directory, name)
        # Strip _task_XXX from end of name
        name_match = re.match(r"(.*)_task_\d+", name)
        if name_match:
            name = name_match.group(1)
        escaped_name = name.replace("_", "-")
        dataset_name = "%s_%s_%s_%s_%s_%s" % ('primary', report_id, escaped_name, 'visible', ext, db_key)
        destination = os.path.join(new_files_directory, dataset_name)
        _copy(source, destination)
        datasets_created.append(escaped_name)

    # Would just assume not have this report, but the multi-file output
    # stuff requires it.
    f = open(report, "w")
    try:
        f.write("Datasets created: %s" % ",".join(datasets_created))
    finally:
        f.close()


def _copy(source, destination):
    try:
        os.link(source, destination)
    except:
        shutil.copy(source, destination)


if __name__ == "__main__":
    main()
