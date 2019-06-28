import argparse
import csv
import sys

from relation_extraction_utils.internal.dep_graph import Step, DepGraph
from relation_extraction_utils.internal.link import Link
from relation_extraction_utils.internal.map_csv_column import CsvColumnMapper
from relation_extraction_utils.internal.ud_types import UdRepresentationPlaceholder


def extract_relations_ud(input, output, triggers, paths, entity_types=None):
    csv_reader = csv.reader(input)
    csv_writer = csv.writer(output)

    required_columns = ['sentence', 'ud_parse', 'lemmas', 'ent1_start', 'ent1_end', 'ent2_start', 'ent2_end']

    if entity_types is not None:
        required_columns.append('ner')

    column_mapper = CsvColumnMapper(next(csv_reader), ['trigger', 'trigger_idx', 'path', 'extraction_comment'],
                                    source_required=required_columns)

    csv_writer.writerow(column_mapper.get_new_headers())

    for counter, entry in enumerate(csv_reader, start=1):

        ud_parse = column_mapper.get_field_value_from_source(entry, 'ud_parse', evaluate=True)
        if ud_parse is None:
            continue

        links = UdRepresentationPlaceholder.get_links_from_ud_dep(ud_parse)

        lemma_indices = column_mapper.get_field_value_from_source(entry, 'lemmas', evaluate=True)
        lemmas = [lemma for _, lemma in lemma_indices]

        word_indices = column_mapper.get_field_value_from_source(entry, 'words', evaluate=True)
        words = [word for _, word in word_indices]


        ent1_start = column_mapper.get_field_value_from_source(entry, 'ent1_start', as_int=True)
        ent1_end = column_mapper.get_field_value_from_source(entry, 'ent1_end', as_int=True)
        if ent1_start is None or ent1_end is None:
            continue
        ent1_indexes = [idx for idx in range(ent1_start, ent1_end + 1)]
        ent1_head = Link.get_head(links, ent1_indexes)

        ent2_start = column_mapper.get_field_value_from_source(entry, 'ent2_start', as_int=True)
        ent2_end = column_mapper.get_field_value_from_source(entry, 'ent2_end', as_int=True)
        if ent2_start is None or ent2_end is None:
            continue

        ent2_indexes = [idx for idx in range(ent2_start, ent2_end + 1)]
        ent2_head = Link.get_head(links, ent2_indexes)

        graph = DepGraph(links)


        if entity_types is not None:
            ner_tags = column_mapper.get_field_value_from_source(entry, 'ner', evaluate=True)

            if ent1_head in ner_tags and ner_tags[ent1_head] != entity_types[0]:
                # print('amazing (1)!!')
                continue

            if ent2_head in ner_tags and ner_tags[ent2_head] != entity_types[1]:
                # print('amazing (2)!!')
                continue

        for trigger_index, (word, lemma) in enumerate(zip(words, lemmas), start=1):

            if word in triggers or lemma in triggers:

                trigger_to_ent2 = Step.get_default_representation(graph.get_steps(trigger_index, ent2_head))
                ent1_to_trigger = Step.get_default_representation(graph.get_steps(ent1_head, trigger_index))
                ent1_to_ent2_via_trigger = '{0} >< {1}'.format(ent1_to_trigger, trigger_to_ent2)

                if ent1_to_ent2_via_trigger in paths:
                    trigger = word if word in triggers else lemma
                    csv_writer.writerow(column_mapper.get_new_row_values(entry, [trigger, trigger_index,
                                                                                 ent1_to_ent2_via_trigger, None]))
                    break

    output.close()


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(
        prog='extract_relations_ud',
        description="identify relationships that match given UD paths and trigger words")

    arg_parser.add_argument(
        'paths',
        action='store',
        metavar='paths-file',
        help='File containing list of paths (each path on separate line)')

    arg_parser.add_argument(
        'triggers',
        action='store',
        metavar='triggers-file',
        help='File containing list of trigger words (each trigger word on separate line)')

    arg_parser.add_argument(
        '--entity-types',
        nargs=2,
        metavar=('entity1-type', 'entity2-type'),
        help='When used this flag should be followed by two named entity types. When provided, the relation identification '
             'algorithm will filter out relations that are marked differently (unmarked relations will not be filtered out)')

    arg_parser.add_argument(
        '--input',
        action='store',
        metavar='input-file',
        help='When provided input will be read from this file rather than from standard input')

    arg_parser.add_argument(
        '--output',
        action='store',
        metavar='output-file',
        help='The comma-separated field output file (if not provided output will be sent to std output)')

    args = arg_parser.parse_args()

    input = open(args.input, encoding='utf-8') if args.input is not None else sys.stdin
    output = open(args.output, 'w', encoding='utf-8', newline='') if args.output is not None else sys.stdout
    triggers = set([line.rstrip('\n') for line in open(args.triggers)])
    paths = set([line.rstrip('\n') for line in open(args.paths)])

    extract_relations_ud(input, output, triggers, paths, args.entity_types)
