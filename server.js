const express = require('express');
const cors = require('cors');
const fs = require('fs');
const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

let parsedData = [];
try {
  const data = fs.readFileSync('../parsed_log.json', 'utf8');
  parsedData = JSON.parse(data);
  console.log(`Loaded ${parsedData.length} log events.`);
} catch (err) {
  console.error("Error reading parsed_log.json:", err);
}

app.get('/api/steps', (req, res) => {
  let results = parsedData;

  if (req.query.bot_id) {
    results = results.filter(event => event.bot_id === req.query.bot_id);
  }

  if (req.query.timestamp) {
    results = results.filter(event => event.timestamp === req.query.timestamp);
  }

  if (req.query.start) {
    const [startX, startY] = req.query.start.split(',').map(Number);
    results = results.filter(event => {
      return event.event === "path_calculation_started" &&
             event.src && 
             event.src.coordinate.x === startX &&
             event.src.coordinate.y === startY;
    });
  }

  if (req.query.dest) {
    const [destX, destY] = req.query.dest.split(',').map(Number);
    results = results.filter(event => {
      return event.event === "path_calculation_started" &&
             event.dest &&
             event.dest.coordinate.x === destX &&
             event.dest.coordinate.y === destY;
    });
  }

  res.json(results);
});

app.get('/api/step/:id', (req, res) => {
  const id = parseInt(req.params.id, 10);
  if (id >= 0 && id < parsedData.length) {
    res.json(parsedData[id]);
  } else {
    res.status(404).json({ error: "Step not found" });
  }
});

app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});
