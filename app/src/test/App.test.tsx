import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// WebGL is unavailable in jsdom; the map is replaced by a stub. The list view covers the same data.
vi.mock("../components/MapView", () => ({ default: () => <div data-testid="map-stub" /> }));

import App from "../App";

const json = readFileSync(resolve(__dirname, "../../public/data/rainguard.json"), "utf8");

function mockFetch(dataOk: boolean) {
  return vi.fn(async (url: string) => {
    if (String(url).includes("rainguard.json")) {
      return dataOk ? new Response(json) : new Response("nope", { status: 500 });
    }
    // forecast service unavailable in tests
    throw new Error("offline");
  });
}

describe("App", () => {
  beforeEach(() => {
    window.matchMedia = vi.fn().mockReturnValue({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() });
    history.replaceState(null, "", "/"); // the app syncs its tab to the hash; start every test on the landing page
  });
  afterEach(() => vi.unstubAllGlobals());

  it("shows a loading state, then the landing page built from real data", async () => {
    vi.stubGlobal("fetch", mockFetch(true));
    render(<App />);
    expect(screen.getByText(/Loading evidence/)).toBeInTheDocument();
    const d = JSON.parse(json);
    const multi = d.locations.filter((l: { n_sources: number }) => l.n_sources >= 2).length;
    expect(await screen.findByText(`Only ${multi} are on more than one official list.`)).toBeInTheDocument();
  });

  it("goes from the landing page to the map with the real location count", async () => {
    vi.stubGlobal("fetch", mockFetch(true));
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: /Explore the map/ }));
    expect(await screen.findByTestId("map-stub")).toBeInTheDocument();
    const n = JSON.parse(json).locations.length;
    await waitFor(() => expect(screen.getByText(String(n))).toBeInTheDocument());
  });

  it("shows an error state instead of fake data when the data file fails", async () => {
    vi.stubGlobal("fetch", mockFetch(false));
    render(<App />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/could not be loaded/);
  });

  it("reports forecast unavailability without inventing values", async () => {
    vi.stubGlobal("fetch", mockFetch(true));
    render(<App />);
    expect(await screen.findByText(/Forecast unavailable right now/)).toBeInTheDocument();
  });

  it("lists places, opens evidence, and shows an honest empty search state", async () => {
    vi.stubGlobal("fetch", mockFetch(true));
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: /Explore the map/ }));
    fireEvent.click(await screen.findByRole("button", { name: "List" }));
    const first = (await screen.findAllByRole("button", { name: /Ward/ }))[0];
    fireEvent.click(first);
    expect(await screen.findByText(/What the official records say/)).toBeInTheDocument();
    expect(screen.getByText((_, el) => el?.tagName === "P" && /not\s+that it is flooded right now/.test(el.textContent ?? ""))).toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText(/Search a place/), { target: { value: "zzzz-nowhere" } });
    expect(await screen.findByText(/does not mean the area is safe/)).toBeInTheDocument();
  }, 20_000); // renders all 251 list rows

  it("renders the insights, plan and method tabs from data", async () => {
    vi.stubGlobal("fetch", mockFetch(true));
    render(<App />);
    await screen.findByText(/Three questions, one screen each/);
    fireEvent.click(screen.getByRole("button", { name: /Insights/ }));
    expect(await screen.findByText("F1", { exact: false })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Plan/ }));
    expect(await screen.findByText(/decision support, not an official directive/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Method/ }));
    expect(await screen.findByText(/location-level forecasting is not/)).toBeInTheDocument();
  });
});
