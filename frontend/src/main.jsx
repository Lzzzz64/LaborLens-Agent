import React from "react";
import { createRoot } from "react-dom/client";

function App() {
  return <main><h1>LaborLens</h1><p>劳动法智能分析服务已启动。</p></main>;
}

createRoot(document.getElementById("root")).render(
  <React.StrictMode><App /></React.StrictMode>,
);
