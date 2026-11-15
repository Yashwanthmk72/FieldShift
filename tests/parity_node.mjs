/* AI-assisted: written with an AI coding assistant (see README, "AI tools used"). */
import { combineScore, normalizePriorities } from "../frontend/lib/scoring.js";
import { readFileSync } from "node:fs";
const cases = JSON.parse(readFileSync(process.argv[2], "utf8"));
console.log(JSON.stringify(cases.map((c) => combineScore(c.components, normalizePriorities(c.priorities)))));
