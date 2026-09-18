import React from "react";
import { render } from "@testing-library/react-native";
import DashboardScreen from "../DashboardScreen";
import * as hooks from "../../api/hooks";

jest.mock("../../api/hooks", () => ({
  useDashboardSummary: jest.fn(),
}));

describe("DashboardScreen", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("renders the total spent value from useDashboardSummary", () => {
    (hooks.useDashboardSummary as jest.Mock).mockReturnValue({
      data: {
        year: 2026,
        month: 9,
        total_spent: 45250.75,
        by_category: [
          { category__name: "Dining", total: 12500.0 },
          { category__name: "Shopping", total: 32750.75 },
        ],
      },
      isLoading: false,
      refetch: jest.fn(),
      isRefetching: false,
    });

    const { getByText, getByTestId } = render(<DashboardScreen />);

    // Assert total spent value appears in the rendered tree
    expect(getByTestId("total-spent-value")).toBeTruthy();
    expect(getByText(/45,250\.75/)).toBeTruthy();
    expect(getByText("Dining")).toBeTruthy();
    expect(getByText("Shopping")).toBeTruthy();
  });
});
