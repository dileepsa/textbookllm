from __future__ import annotations

import argparse
from .models import QueryRequest
from .services.pipeline import DefaultPipeline


def main() -> None:
	parser = argparse.ArgumentParser(prog="textbookllm")
	sub = parser.add_subparsers(dest="cmd", required=True)

	p_ingest = sub.add_parser("ingest", help="Ingest a local text file")
	p_ingest.add_argument("path", help="Path to file")

	p_query = sub.add_parser("query", help="Query the knowledge base")
	p_query.add_argument("q", help="Question text")
	p_query.add_argument("-k", type=int, default=5)

	args = parser.parse_args()
	pipeline = DefaultPipeline()

	if args.cmd == "ingest":
		res = pipeline.ingest(args.path)
		print(f"OK document_id={res.document.id} chunks={res.num_chunks}")
	elif args.cmd == "query":
		resp = pipeline.query(QueryRequest(query=args.q, max_results=args.k))
		print(resp.answer)
	else:
		parser.print_help()


if __name__ == "__main__":
	main()
