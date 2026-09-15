import { checkBackendHealth, analyzeWfdb, ApiError } from "@/lib/api";

describe("checkBackendHealth", () => {
  afterEach(() => jest.resetAllMocks());

  it("returns ok:true when the health route responds ok", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ ok: true }),
    }) as jest.Mock;

    const result = await checkBackendHealth();
    expect(result.ok).toBe(true);
  });

  it("returns ok:false when the backend is unreachable", async () => {
    global.fetch = jest.fn().mockRejectedValue(new Error("network error"));

    const result = await checkBackendHealth();
    expect(result.ok).toBe(false);
  });

  it("returns ok:false on a non-200 response without throwing", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 502,
      json: async () => ({}),
    }) as jest.Mock;

    const result = await checkBackendHealth();
    expect(result.ok).toBe(false);
  });
});

describe("analyzeWfdb", () => {
  afterEach(() => jest.resetAllMocks());

  it("throws ApiError with backend detail message on failure", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ detail: "No complete WFDB .hea/.dat record found." }),
    }) as jest.Mock;

    const file = new File(["data"], "record.dat");
    await expect(analyzeWfdb([file])).rejects.toThrow(ApiError);
    await expect(analyzeWfdb([file])).rejects.toThrow(
      /No complete WFDB/
    );
  });

  it("resolves with parsed JSON on success", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ af_detection_score: 0.12 }),
    }) as jest.Mock;

    const file = new File(["data"], "record.dat");
    const result = await analyzeWfdb([file]);
    expect(result).toEqual({ af_detection_score: 0.12 });
  });

  it("wraps network failure in ApiError rather than throwing raw", async () => {
    global.fetch = jest.fn().mockRejectedValue(new Error("Failed to fetch"));

    const file = new File(["data"], "record.dat");
    await expect(analyzeWfdb([file])).rejects.toThrow(ApiError);
  });
});
