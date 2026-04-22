/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    "./src/lychd/**/*.html",
    "./src/lychd/**/*.j2",
    "./resources/**/*.{js,ts,css}",
  ],
  theme: {
    extend: {
      colors: {
        // Frostmourne: The Tri-Color Palette
        void: {
          DEFAULT: "#08080b", // Deep Void Black
          light: "#12121a",   // Slightly lighter for cards/code
        },
        arcane: "#7c4dff",     // Deep Magic (Purple)
        frost: "#00e5ff",      // Ice Chill (Blue)
        necro: "#00ff9d",      // Matrix Code (Green)
      },
      fontFamily: {
        sans: ["Inter", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [
    require("@tailwindcss/forms"),
    require("@tailwindcss/typography"),
  ],
}
