"use client";

import Link from "next/link";
import { useState } from "react";


const BACKEND = "http://127.0.0.1:8000";


const filters = [
  "All",
  "Video",
  "Reading",
  "Demo",
  "Assignment",
];


type SearchResult = {
  id: number;
  course: string;
  sheet_name: string;
  module: string;
  type: string;
  title: string;
  source_file: string | null;
  google_sheet: string | null;
  relevance_score: number;
};


export default function Home() {
  const [query, setQuery] = useState("");
  const [type, setType] = useState("All");

  const [results, setResults] =
    useState<SearchResult[]>([]);

  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState("");
  const [correctedQuery, setCorrectedQuery] = useState("");
  const [queryWasCorrected, setQueryWasCorrected] = useState(false);


  async function search(
    selectedType = type
  ) {
    setLoading(true);
    setSearched(true);
    setError("");

    try {
      const response = await fetch(
        `${BACKEND}/search?query=${encodeURIComponent(
          query
        )}&type=${encodeURIComponent(selectedType)}`
      );

      if (!response.ok) {
        throw new Error("Search request failed.");
      }

      const data = await response.json();

      setResults(data.results ?? []);

setCorrectedQuery(data.corrected_query ?? "");

setQueryWasCorrected(
  data.query_was_corrected ?? false
);

    } catch (searchError) {
      console.error(searchError);

      setError(
        "Could not connect to the CourseIQ backend."
      );

      setResults([]);
      setCorrectedQuery("");

setQueryWasCorrected(false);

    } finally {
      setLoading(false);
    }
  }


  function selectFilter(
    selectedType: string
  ) {
    setType(selectedType);

    if (searched) {
      search(selectedType);
    }
  }


  function icon(
    contentType: string
  ) {
    const value = contentType.toLowerCase();

    if (value === "video") return "🎥";

    if (
      value === "reading"
      || value === "article"
    ) {
      return "📖";
    }

    if (
      value === "demo"
      || value === "demonstration"
      || value === "lab"
    ) {
      return "💻";
    }

    if (
      value.includes("assignment")
      || value.includes("quiz")
      || value.includes("project")
    ) {
      return "📝";
    }

    return "📄";
  }


  return (
    <main className="min-h-screen bg-slate-100 px-5 py-12 text-slate-900">
      <div className="mx-auto max-w-6xl">

        <header className="mb-10">
          <div className="flex items-start justify-between gap-5">
            <div>
              <h1 className="text-5xl font-bold tracking-tight">
                CourseIQ
              </h1>

              <p className="mt-3 text-lg text-slate-600">
                AI-powered search across every course,
                workbook and sheet.
              </p>
            </div>

            <Link
              href="/admin"
              className="rounded-xl border border-slate-300 bg-white px-5 py-3 font-semibold hover:bg-slate-50"
            >
              Admin
            </Link>
          </div>
        </header>

        <section className="rounded-2xl bg-white p-7 shadow-sm">
          <div className="flex flex-col gap-4 md:flex-row">
            <input
              value={query}
              onChange={(event) =>
                setQuery(event.target.value)
              }
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  search();
                }
              }}
              placeholder="Try CNN, transformer attention, Python graphs..."
              className="flex-1 rounded-xl border border-slate-300 px-5 py-4 text-lg outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            />

            <button
              onClick={() => search()}
              disabled={loading}
              className="rounded-xl bg-blue-600 px-9 py-4 font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
            >
              {loading
                ? "Searching..."
                : "Search"}
            </button>
          </div>

          <div className="mt-5 flex flex-wrap gap-3">
            {filters.map((filter) => (
              <button
                key={filter}
                onClick={() =>
                  selectFilter(filter)
                }
                className={`rounded-full px-5 py-2.5 font-medium transition ${
                  type === filter
                    ? "bg-blue-600 text-white"
                    : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                }`}
              >
                {filter}
              </button>
            ))}
          </div>
        </section>

        {error && (
          <div className="mt-6 rounded-xl border border-red-200 bg-red-50 p-4 text-red-700">
            {error}
          </div>
        )}

        {searched &&
  !loading &&
  !error &&
  queryWasCorrected &&
  correctedQuery && (
    <div className="mt-6 rounded-xl border border-amber-300 bg-amber-50 p-4">
      <span className="text-slate-700">
        Showing results for{" "}
      </span>

      <button
        onClick={() => {
  setQuery(correctedQuery);

  setTimeout(() => {
    search();
  }, 0);
}}
        className="font-semibold text-blue-700 hover:underline"
      >
        {correctedQuery}
      </button>
    </div>
)}

        {searched && !loading && !error && (
          <div className="mt-8 text-slate-600">
            {results.length} relevant result
            {results.length === 1 ? "" : "s"}
          </div>
        )}

        {searched
          && !loading
          && !error
          && results.length === 0 && (
            <div className="mt-6 rounded-2xl bg-white p-10 text-center shadow-sm">
              <h2 className="text-xl font-semibold">
                No relevant content found
              </h2>

              <p className="mt-2 text-slate-500">
                Try another phrase, acronym or filter.
              </p>
            </div>
          )}

        <div className="mt-6 space-y-5">
          {results.map((item) => (
            <article
              key={item.id}
              className="rounded-2xl bg-white p-7 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
            >
              <div className="flex flex-col gap-6 lg:flex-row lg:justify-between">

                <div className="flex-1">
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="rounded-full bg-blue-50 px-3 py-1 text-sm font-semibold text-blue-700">
                      {icon(item.type)} {item.type}
                    </span>

                    <span className="rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-600">
                      {item.sheet_name}
                    </span>
                  </div>

                  <h2 className="mt-4 text-2xl font-bold">
                    {item.title}
                  </h2>

                  <div className="mt-5 grid gap-5 md:grid-cols-2">
                    <div>
                      <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">
                        Course
                      </p>

                      <p className="mt-1 text-lg">
                        {item.course}
                      </p>
                    </div>

                    <div>
                      <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">
                        Sheet
                      </p>

                      <p className="mt-1 text-lg">
                        {item.sheet_name}
                      </p>
                    </div>

                    <div className="md:col-span-2">
                      <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">
                        Module
                      </p>

                      <p className="mt-1 text-lg">
                        {item.module || "Not specified"}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="flex min-w-56 flex-col gap-3">
                  {item.source_file && (
                    <a
                      href={`${BACKEND}/download/${encodeURIComponent(
                        item.source_file
                      )}`}
                      className="rounded-xl bg-slate-900 px-5 py-3 text-center font-semibold text-white hover:bg-slate-700"
                    >
                      Download Workbook
                    </a>
                  )}

                  {item.google_sheet && (
                    <a
                      href={item.google_sheet}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="rounded-xl border border-blue-600 px-5 py-3 text-center font-semibold text-blue-600 hover:bg-blue-50"
                    >
                      Open Google Sheet
                    </a>
                  )}
                </div>

              </div>
            </article>
          ))}
        </div>

      </div>
    </main>
  );
}