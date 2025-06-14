module.exports = {
  root: true,
  env: {
    browser: true,
    es2021: true,
    node: true, // 允许 Node.js 全局变量
  },
  extends: [
    "eslint:recommended",
    "plugin:vue/vue3-essential",
  ],
  parserOptions: {
    ecmaVersion: 12,
    sourceType: "module",
  },
  globals: {
    defineProps: "readonly",
  },
  rules: {
    "vue/multi-word-component-names": "off",
    "no-undef": "error",
    "no-unused-vars": "off",
    'prettier/prettier': 'off'
  },
};
