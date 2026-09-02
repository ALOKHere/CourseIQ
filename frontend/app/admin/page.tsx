"use client";

import Link from "next/link";
import {
  FormEvent,
  useState,
} from "react";


const BACKEND = "http://127.0.0.1:8000";


type UploadResponse = {
  message: string;
  course: string;
  source_kind: string;
  rows_imported: number;
  sheets_imported: number;
  sheet_names: string[];
  source_file: string;
  google_sheet: string;
};


export default function AdminPage() {
  const [courseName, setCourseName] = useState("");
  const [googleSheet, setGoogleSheet] = useState("");
  const [file, setFile] = useState<File | null>(null);

  const [uploading, setUploading] = useState(false);
  const [result, setResult] =
    useState<UploadResponse | null>(null);

  const [error, setError] = useState("");


  async function uploadCourse(
    event: FormEvent
  ) {
    event.preventDefault();

    setError("");
    setResult(null);

    if (!courseName.trim()) {
      setError("Enter the course name.");
      return;
    }

    if (!file && !googleSheet.trim()) {
      setError(
        "Provide an Excel file or a Google Sheets link."
      );
      return;
    }

    const formData = new FormData();

    formData.append(
      "course_name",
      courseName.trim()
    );

    formData.append(
      "google_sheet",
      googleSheet.trim()
    );

    if (file) {
      formData.append(
        "file",
        file
      );
    }

    setUploading(true);

    try {
      const response = await fetch(
        `${BACKEND}/upload`,
        {
          method: "POST",
          body: formData,
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Course upload failed."
        );
      }

      setResult(data);

      setCourseName("");
      setGoogleSheet("");
      setFile(null);

      const input = document.getElementById(
        "excel-file"
      ) as HTMLInputElement | null;

      if (input) {
        input.value = "";
      }

    } catch (uploadError) {
      console.error(uploadError);

      setError(
        uploadError instanceof Error
          ? uploadError.message
          : "Course upload failed."
      );

    } finally {
      setUploading(false);
    }
  }


  return (
    <main className="min-h-screen bg-slate-100 px-5 py-12 text-slate-900">
      <div className="mx-auto max-w-3xl">

        <Link
          href="/"
          className="font-semibold text-blue-600 hover:underline"
        >
          ← Back to search
        </Link>

        <header className="mt-6">
          <h1 className="text-4xl font-bold">
            CourseIQ Admin
          </h1>

          <p className="mt-2 text-slate-600">
            Import a complete course using an Excel workbook
            or a Google Sheets link.
          </p>
        </header>

        <form
          onSubmit={uploadCourse}
          className="mt-8 rounded-2xl bg-white p-8 shadow-sm"
        >
          <div>
            <label className="mb-2 block font-semibold">
              Course name
              <span className="ml-1 text-red-500">*</span>
            </label>

            <input
              value={courseName}
              onChange={(event) =>
                setCourseName(event.target.value)
              }
              placeholder="Example: Transfer Learning Specialization"
              className="w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            />
          </div>

          <div className="mt-7">
            <h2 className="text-lg font-bold">
              Choose one source
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              Upload an Excel workbook, paste a Google Sheets
              link, or provide both.
            </p>
          </div>

          <div className="mt-5">
            <label className="mb-2 block font-semibold">
              Excel workbook
              <span className="ml-2 text-sm font-normal text-slate-500">
                Optional
              </span>
            </label>

            <input
              id="excel-file"
              type="file"
              accept=".xlsx"
              onChange={(event) =>
                setFile(
                  event.target.files?.[0] ?? null
                )
              }
              className="w-full rounded-xl border border-slate-300 p-3"
            />

            <p className="mt-2 text-sm text-slate-500">
              Every worksheet inside the workbook will be read.
            </p>
          </div>

          <div className="my-7 flex items-center gap-4">
            <div className="h-px flex-1 bg-slate-200" />

            <span className="text-sm font-semibold text-slate-400">
              OR
            </span>

            <div className="h-px flex-1 bg-slate-200" />
          </div>

          <div>
            <label className="mb-2 block font-semibold">
              Google Sheets link
              <span className="ml-2 text-sm font-normal text-slate-500">
                Optional
              </span>
            </label>

            <input
              type="url"
              value={googleSheet}
              onChange={(event) =>
                setGoogleSheet(event.target.value)
              }
              placeholder="https://docs.google.com/spreadsheets/d/..."
              className="w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            />

            <p className="mt-2 text-sm text-slate-500">
              The sheet must allow viewing through its shared
              link. Every tab in the workbook will be imported.
            </p>
          </div>

          <button
            type="submit"
            disabled={uploading}
            className="mt-8 w-full rounded-xl bg-blue-600 px-6 py-4 font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {uploading
              ? "Importing all sheets..."
              : "Import Course"}
          </button>
        </form>

        {error && (
          <div className="mt-6 rounded-xl border border-red-200 bg-red-50 p-4 text-red-700">
            {error}
          </div>
        )}

        {result && (
          <section className="mt-6 rounded-2xl border border-green-200 bg-green-50 p-6">
            <h2 className="text-xl font-bold text-green-800">
              Course imported successfully
            </h2>

            <div className="mt-4 space-y-2 text-green-900">
              <p>
                <strong>Course:</strong>{" "}
                {result.course}
              </p>

              <p>
                <strong>Source:</strong>{" "}
                {result.source_kind === "google_sheet"
                  ? "Google Sheets"
                  : "Excel workbook"}
              </p>

              <p>
                <strong>Sheets imported:</strong>{" "}
                {result.sheets_imported}
              </p>

              <p>
                <strong>Content items:</strong>{" "}
                {result.rows_imported}
              </p>
            </div>

            <div className="mt-5">
              <p className="font-semibold text-green-900">
                Imported tabs
              </p>

              <div className="mt-3 flex flex-wrap gap-2">
                {result.sheet_names.map((sheet) => (
                  <span
                    key={sheet}
                    className="rounded-full bg-white px-3 py-1.5 text-sm font-medium text-green-800"
                  >
                    {sheet}
                  </span>
                ))}
              </div>
            </div>
          </section>
        )}

      </div>
    </main>
  );
}