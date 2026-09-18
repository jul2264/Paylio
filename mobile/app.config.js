module.exports = {
  expo: {
    name: "Paylio",
    slug: "paylio",
    version: "1.0.0",
    orientation: "portrait",
    userInterfaceStyle: "dark",
    ios: {
      supportsTablet: true,
      bundleIdentifier: "com.paylio.app",
    },
    android: {
      package: "com.paylio.app",
    },
    extra: {
      apiUrl: process.env.EXPO_PUBLIC_API_BASE_URL || "http://10.0.2.2:8000/api/v1",
      eas: {
        projectId: "paylio-mobile-project-id",
      },
    },
  },
};
