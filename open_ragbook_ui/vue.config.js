const { defineConfig } = require("@vue/cli-service");
module.exports = {
  devServer: {
    proxy: {
      "/api": {
        target: process.env.VUE_APP_API_BASE_URL, // 使用环境变量中的 API 前缀
        changeOrigin: true,
        pathRewrite: { "^/api": "" },
      },
    },
    client: {
      overlay: {
        warnings: false,
        runtimeErrors: (error) => {
          const ignoreErrors = [
            "ResizeObserver loop limit exceeded",
            "ResizeObserver loop completed with undelivered notifications.",
          ];
          if (ignoreErrors.includes(error.message)) {
            return false;
          }
        },
      },
    },
  },
};
