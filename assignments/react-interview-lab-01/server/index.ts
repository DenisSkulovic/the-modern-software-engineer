import { createApp } from "./app";
import express from "express";
import { resolve } from "node:path";
const app = createApp();
if (process.env.NODE_ENV === "production")
  app.use(express.static(resolve("dist/client")));
app.listen(4173, "127.0.0.1", () =>
  console.log("RelayOps API listening at http://127.0.0.1:4173"),
);
