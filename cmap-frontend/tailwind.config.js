/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",  // ✅ 让 src 目录下所有组件都能用 Tailwind
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}

