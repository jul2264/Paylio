import * as SecureStore from "expo-secure-store";
import { api } from "../client";

// Mock expo-secure-store
jest.mock("expo-secure-store", () => ({
  getItemAsync: jest.fn(),
  setItemAsync: jest.fn(),
  deleteItemAsync: jest.fn(),
}));

// Mock global fetch
const mockFetch = jest.fn();
(global as any).fetch = mockFetch;

describe("API Client", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("attaches Authorization header when a token is stored", async () => {
    (SecureStore.getItemAsync as jest.Mock).mockImplementation((key: string) => {
      if (key === "paylio_access_token") {
        return Promise.resolve("mock_jwt_access_token_123");
      }
      return Promise.resolve(null);
    });

    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ results: [] }),
    });

    await api.get("/transactions/");

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const calledUrl = mockFetch.mock.calls[0][0];
    const calledOptions = mockFetch.mock.calls[0][1];

    expect(calledUrl).toContain("/transactions/");
    expect(calledOptions.headers).toBeDefined();
    expect(calledOptions.headers["Authorization"]).toBe(
      "Bearer mock_jwt_access_token_123"
    );
  });

  test("omits Authorization header when no token is stored", async () => {
    (SecureStore.getItemAsync as jest.Mock).mockResolvedValue(null);

    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ gold: {} }),
    });

    await api.get("/rates/");

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const calledUrl = mockFetch.mock.calls[0][0];
    const calledOptions = mockFetch.mock.calls[0][1];

    expect(calledUrl).toContain("/rates/");
    expect(calledOptions.headers).toBeDefined();
    expect(calledOptions.headers["Authorization"]).toBeUndefined();
  });
});
