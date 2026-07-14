/* =========================================================
   F1 Interactive 3D CAD Viewer  — cad3d.js
   Pure Canvas 2D, no external dependencies.
   Painter's-algorithm flat-shaded polygon renderer.
   ========================================================= */

(function () {

  // ── Geometry definitions for each component ─────────────────────────────

  function getRearWingGeometry(setup, drsActive) {
    const highDownforce = setup === 'High Downforce';
    const mainAngle = highDownforce ? 0.28 : 0.10;   // radians camber
    // When DRS is active, the flap angle is nearly flat (e.g. 0.03 radians)
    const flapAngle = drsActive ? 0.03 : (highDownforce ? 0.42 : 0.14);

    const W = 100;  // half-span
    const panels = [];
    const STEPS = 12; // spanwise divisions

    // ── Mainplane: curved airfoil cross-section swept across span ──
    function mainY(t) { return -Math.sin(t * Math.PI) * 18 * (highDownforce ? 1.5 : 0.7); }
    function mainZ(t) { return (t - 0.5) * 60; }

    for (let i = 0; i < STEPS; i++) {
      const t0 = i / STEPS, t1 = (i + 1) / STEPS;
      const x0 = -W + i * (2 * W / STEPS), x1 = -W + (i + 1) * (2 * W / STEPS);
      // chord profile: 4 verts forming a thick airfoil slice
      const chord = 50;
      const yl0 = mainY(t0), yl1 = mainY(t1);
      panels.push({
        verts: [
          [x0, -12 + yl0, -chord * 0.5],
          [x1, -12 + yl1, -chord * 0.5],
          [x1,  -4 + yl1,  chord * 0.5],
          [x0,  -4 + yl0,  chord * 0.5],
        ],
        color: '#0e3d50', edge: '#1f5b75', label: null
      });
      // bottom skin
      panels.push({
        verts: [
          [x0, -14 + yl0, -chord * 0.5],
          [x1, -14 + yl1, -chord * 0.5],
          [x1, -12 + yl1, -chord * 0.5],
          [x0, -12 + yl0, -chord * 0.5],
        ],
        color: '#0a2a38', edge: '#14465b', label: null
      });
    }

    // ── DRS Flap ──
    const flapThick = 8, flapChord = 30;
    const flapYBase = highDownforce ? -28 : -20;
    for (let i = 0; i < STEPS; i++) {
      const x0 = -W + i * (2 * W / STEPS), x1 = -W + (i + 1) * (2 * W / STEPS);
      const t0 = i / STEPS, t1 = (i + 1) / STEPS;
      const fc0 = Math.sin(t0 * Math.PI) * flapAngle * 18;
      const fc1 = Math.sin(t1 * Math.PI) * flapAngle * 18;
      panels.push({
        verts: [
          [x0, flapYBase - fc0,           18],
          [x1, flapYBase - fc1,           18],
          [x1, flapYBase - fc1 + flapThick, 18 + flapChord],
          [x0, flapYBase - fc0 + flapThick, 18 + flapChord],
        ],
        color: '#3d0e20', edge: '#5a1932', label: null
      });
    }

    // ── Left Endplate ──
    const epH = 50, epD = 80;
    panels.push({
      verts: [[-W,  0,    -30], [-W,  0,    50], [-W, -epH, 50], [-W, -epH, -30]],
      color: '#1a1c22', edge: '#2d3038', label: 'Endplate'
    });
    // ── Right Endplate ──
    panels.push({
      verts: [[W,  0,    -30], [W,  0,    50], [W, -epH, 50], [W, -epH, -30]],
      color: '#1a1c22', edge: '#2d3038', label: null
    });

    // ── DRS Actuator pillar ──
    const pW = 4;
    panels.push({
      verts: [[-pW, -14, -25], [pW, -14, -25], [pW, -40, -25], [-pW, -40, -25]],
      color: '#ffffff', edge: '#dddddd', label: 'DRS Actuator'
    });

    // ── Airflow streamlines (line lists) ──
    const lines = [];
    for (let s = -60; s <= 60; s += 20) {
      const pts = [];
      for (let z = -120; z <= 120; z += 10) {
        const maxDeflect = drsActive ? -3 : (highDownforce ? -28 : -12);
        const deflect = z > -25 && z < 60
          ? Math.sin((z + 25) / 85 * Math.PI) * maxDeflect
          : 0;
        pts.push([s, 10 + deflect, z]);
      }
      lines.push({ pts, color: z => z < 0 ? '#00ffff' : '#ff00ff' });
    }

    return { panels, lines };
  }


  function getFrontWingGeometry(setup) {
    const highDownforce = setup === 'High Downforce';
    const panels = [];
    const lines = [];
    const STEPS = 14;
    const halfSpan = 120;

    // ── Main Plane (left & right) ──
    for (let side = -1; side <= 1; side += 2) {
      for (let i = 0; i < STEPS / 2; i++) {
        const x0 = side * (20 + i * ((halfSpan - 20) / (STEPS / 2)));
        const x1 = side * (20 + (i + 1) * ((halfSpan - 20) / (STEPS / 2)));
        const sweep = Math.abs(x0) * 0.15;
        panels.push({
          verts: [
            [x0,  4,  -30 - sweep],
            [x1,  4,  -30 - Math.abs(x1) * 0.15],
            [x1,  0,   10 - Math.abs(x1) * 0.15],
            [x0,  0,   10 - sweep],
          ],
          color: '#0e3d50', edge: '#1e5a75', label: i === 3 && side === 1 ? 'Main Plane' : null
        });
      }
    }

    // ── Cascade flaps (2 additional elements) ──
    const flapColors = ['#0e3d2f', '#3d0e20'];
    const flapEdges  = ['#1d5b47', '#5a1932'];
    for (let f = 0; f < 2; f++) {
      for (let side = -1; side <= 1; side += 2) {
        for (let i = 0; i < STEPS / 2; i++) {
          const x0 = side * (20 + i * ((halfSpan - 20) / (STEPS / 2)));
          const x1 = side * (20 + (i + 1) * ((halfSpan - 20) / (STEPS / 2)));
          const sweep = Math.abs(x0) * 0.15;
          const yOff = (f + 1) * (highDownforce ? 10 : 7);
          panels.push({
            verts: [
              [x0, -yOff + 4, -30 - sweep - (f + 1) * 8],
              [x1, -yOff + 4, -30 - Math.abs(x1) * 0.15 - (f + 1) * 8],
              [x1, -yOff,      10 - Math.abs(x1) * 0.15 - (f + 1) * 8],
              [x0, -yOff,      10 - sweep - (f + 1) * 8],
            ],
            color: flapColors[f], edge: flapEdges[f], label: null
          });
        }
      }
    }

    // ── Nose cone ──
    panels.push({
      verts: [[-18, 0, -30], [18, 0, -30], [18, 8, 80], [-18, 8, 80]],
      color: '#1e222b', edge: '#313642', label: 'Nose Cone'
    });
    panels.push({
      verts: [[-18, 0, -30], [18, 0, -30], [18, -6, 80], [-18, -6, 80]],
      color: '#161820', edge: '#282b36', label: null
    });

    // ── Endplates ──
    panels.push({
      verts: [[-halfSpan, 8, -60], [-halfSpan, 8, 20], [-halfSpan, -20, 20], [-halfSpan, -20, -60]],
      color: '#1a1c22', edge: '#2d3038', label: 'Endplate'
    });
    panels.push({
      verts: [[halfSpan, 8, -60], [halfSpan, 8, 20], [halfSpan, -20, 20], [halfSpan, -20, -60]],
      color: '#1a1c22', edge: '#2d3038', label: null
    });

    // ── Airflow outwash streamlines ──
    for (let y = -15; y <= 10; y += 5) {
      const pts = [];
      for (let z = -80; z <= 60; z += 8) {
        const deflect = z > -40 && z < 20 ? Math.cos((z + 40) / 60 * Math.PI) * -15 : 0;
        pts.push([130 + deflect * 0.5, y, z]);
      }
      lines.push({ pts, color: '#00ffff' });
    }

    return { panels, lines };
  }

  function getChassisGeometry(setup) {
    const panels = [];
    const lines = [];

    // ── Monocoque body ──
    const bodyVerts = [
      // bottom vertices (front→rear)
      [-30, 0,  -180], [30, 0, -180],  // nose tip bottom
      [-45, 0,  -80],  [45, 0, -80],   // front suspension
      [-55, 0,   40],  [55, 0,  40],   // sidepod front
      [-60, 0,  140],  [60, 0, 140],   // sidepod rear
      [-40, 0,  210],  [40, 0, 210],   // rear narrow
    ];
    const topH = 35;
    // Side panels (left, 8 segments)
    for (let i = 0; i < 4; i++) {
      const bl = bodyVerts[i * 2], nl = bodyVerts[(i + 1) * 2];
      panels.push({
        verts: [
          [bl[0], bl[1],      bl[2]],
          [bl[0], bl[1] + topH, bl[2]],
          [nl[0], nl[1] + topH, nl[2]],
          [nl[0], nl[1],      nl[2]],
        ],
        color: i < 2 ? '#0d2535' : '#122035', edge: '#00ffff', label: i === 2 ? 'Monocoque' : null
      });
      // Right side
      const br = bodyVerts[i * 2 + 1], nr = bodyVerts[(i + 1) * 2 + 1];
      panels.push({
        verts: [
          [br[0], br[1],      br[2]],
          [br[0], br[1] + topH, br[2]],
          [nr[0], nr[1] + topH, nr[2]],
          [nr[0], nr[1],      nr[2]],
        ],
        color: i < 2 ? '#0d2535' : '#122035', edge: '#00cccc', label: null
      });
    }

    // ── Roll hoop ──
    panels.push({
      verts: [[-10, topH, -20], [10, topH, -20], [10, topH + 45, -10], [-10, topH + 45, -10]],
      color: '#2b0e17', edge: '#ff0055', label: 'Roll Hoop'
    });

    // ── Sidepod intakes ──
    for (let s = -1; s <= 1; s += 2) {
      panels.push({
        verts: [
          [s * 55, 2,   40], [s * 70, 2,   40],
          [s * 70, 22,  40], [s * 55, 22,  40],
        ],
        color: '#0e2d1e', edge: '#00ff88', label: s === -1 ? 'Sidepod Intake' : null
      });
    }

    // ── Floor (venturi tunnels) ──
    for (let s = -1; s <= 1; s += 2) {
      panels.push({
        verts: [
          [s * 30, 0, 20],  [s * 60, 0, 20],
          [s * 55, 0, 200], [s * 25, 0, 200],
        ],
        color: '#0a1a10', edge: '#00ff88', label: null
      });
    }

    // ── Airflow streamlines over body ──
    for (let x = -50; x <= 50; x += 20) {
      const pts = [];
      for (let z = -200; z <= 220; z += 15) {
        let y = topH + 10;
        if (z > -80 && z < 160) {
          y = topH + 10 + Math.sin((z + 80) / 240 * Math.PI) * 15;
        }
        pts.push([x, y, z]);
      }
      lines.push({ pts, color: '#00ffff' });
    }

    return { panels, lines };
  }

  function getFastenerGeometry(setup, nomDiam, length) {
    const panels = [];
    const lines = [];

    // Scale small fastener up to fill the viewport (base max dimension is normalized to 150 units)
    const scale = Math.max(1.0, 150 / Math.max(nomDiam * 2.2, length));
    const d = nomDiam * scale;
    const l = length * scale;
    const r = d / 2;

    if (setup === 'Bolt') {
      const segs = 10;
      const headDiam = d * 1.6;
      const headH = d * 0.8;
      const headR = headDiam / 2;

      // Hex head vertices
      const headVertsTop = [];
      const headVertsBot = [];
      for (let i = 0; i < 6; i++) {
        const theta = (i / 6) * Math.PI * 2;
        const hx = Math.cos(theta) * headR;
        const hy = Math.sin(theta) * headR;
        headVertsBot.push([hx, hy, 0]);
        headVertsTop.push([hx, hy, -headH]);
      }

      // Hex top cap
      panels.push({
        verts: headVertsTop,
        color: '#4e515a', edge: '#636772', label: 'Hex Bolt Head'
      });

      // Hex sides
      for (let i = 0; i < 6; i++) {
        const next = (i + 1) % 6;
        panels.push({
          verts: [
            headVertsBot[i],
            headVertsBot[next],
            headVertsTop[next],
            headVertsTop[i]
          ],
          color: '#3d3f47', edge: '#4f525c', label: null
        });
      }

      // Shank cylinder with actual physical thread ridges
      const threadSteps = Math.floor(l / (d * 0.1));
      let prevRing = [];
      for (let j = 0; j < segs; j++) {
        const theta = (j / segs) * Math.PI * 2;
        const sx = Math.cos(theta) * r;
        const sy = Math.sin(theta) * r;
        prevRing.push([sx, sy, 0]);
      }
      
      // Connection cap
      panels.push({
        verts: prevRing,
        color: '#24262b', edge: '#3f414a', label: null
      });

      // Loop along length to build thread ridges
      for (let step = 1; step <= threadSteps; step++) {
        const zPos = (step / threadSteps) * l;
        // Alternate radius to create crests and roots
        const isCrest = step % 2 === 0;
        const stepR = r * (isCrest ? 1.08 : 0.82); // deeper V-shape thread profiles!
        
        const nextRing = [];
        for (let j = 0; j < segs; j++) {
          const theta = (j / segs) * Math.PI * 2;
          const sx = Math.cos(theta) * stepR;
          const sy = Math.sin(theta) * stepR;
          nextRing.push([sx, sy, zPos]);
        }
        
        // Draw cylinder segment faces between prevRing and nextRing
        const pColor = isCrest ? '#7e828f' : '#2b2c31';
        const eColor = isCrest ? '#9aa0b0' : '#3f414a';
        for (let j = 0; j < segs; j++) {
          const next = (j + 1) % segs;
          panels.push({
            verts: [
              prevRing[j],
              prevRing[next],
              nextRing[next],
              nextRing[j]
            ],
            color: pColor, 
            edge: eColor,
            isThread: true,
            label: step === Math.floor(threadSteps / 2) && j === 2 ? `M${nomDiam} Thread` : null
          });
        }

        prevRing = nextRing;
      }
      
      // End cap of the threaded shank
      panels.push({
        verts: prevRing.slice().reverse(),
        color: '#1a1b1e', edge: '#2e3037', label: null
      });

    } else if (setup === 'Nut') {
      const headDiam = d * 1.6;
      const headH = d * 0.8;
      const headR = headDiam / 2;

      const outerTop = [];
      const outerBot = [];
      
      const threadSteps = 8;
      const segs = 12;

      // Generates inner vertices for internal threading
      const innerRings = [];
      for (let step = 0; step <= threadSteps; step++) {
        const zPos = (step / threadSteps) * headH;
        // step % 2 === 1 makes step 0 (bottom) and step 8 (top) roots (wide), creating a chamfer slope!
        const isCrest = step % 2 === 1;
        const stepR = r * (isCrest ? 0.80 : 1.20); // slightly deeper thread profiles!
        const ring = [];
        for (let i = 0; i < segs; i++) {
          const theta = (i / segs) * Math.PI * 2;
          ring.push([Math.cos(theta) * stepR, Math.sin(theta) * stepR, zPos]);
        }
        innerRings.push(ring);
      }

      // Outer hex vertices
      for (let i = 0; i < 6; i++) {
        const theta = (i / 6) * Math.PI * 2;
        outerBot.push([Math.cos(theta) * headR, Math.sin(theta) * headR, 0]);
        outerTop.push([Math.cos(theta) * headR, Math.sin(theta) * headR, headH]);
      }

      // Outer hex side panels (using polished blue-grey steel shades for high shine!)
      for (let i = 0; i < 6; i++) {
        const next = (i + 1) % 6;
        panels.push({
          verts: [
            outerBot[i],
            outerBot[next],
            outerTop[next],
            outerTop[i]
          ],
          color: '#5e6270', edge: '#7e8396', label: i === 2 ? `Hex Nut (M${nomDiam})` : null
        });
      }

      // Inner thread cylinder walls (creates corrugated inner ridges)
      for (let step = 0; step < threadSteps; step++) {
        const isCrest = step % 2 === 1;
        // Match the shiny bolt shank crest colors (#7e828f) and root shadow colors
        const pColor = isCrest ? '#7e828f' : '#32343a';
        const eColor = isCrest ? '#9aa0b0' : '#45474f';
        for (let i = 0; i < segs; i++) {
          const next = (i + 1) % segs;
          panels.push({
            verts: [
              innerRings[step][next],
              innerRings[step][i],
              innerRings[step+1][i],
              innerRings[step+1][next]
            ],
            color: pColor,
            edge: eColor,
            isThread: true,
            isInner: true,
            label: null
          });
        }
      }

      // Top and bottom faces with central hole
      const topRing = innerRings[threadSteps];
      const botRing = innerRings[0];

      // Divide top and bottom faces to connect outer hex bounds to inner hole bounds
      for (let i = 0; i < 6; i++) {
        const next = (i + 1) % 6;
        const idx0 = 2 * i;
        const idx1 = 2 * i + 1;
        const idx2 = (2 * i + 2) % 12;
        
        // Top cap slice sector quad (edge color matches face color for seamless single slab look)
        panels.push({
          verts: [
            topRing[idx0],
            outerTop[i],
            outerTop[next],
            topRing[idx1]
          ],
          color: '#4b4f5a', edge: '#4b4f5a', label: i === 2 ? 'Internal Thread' : null
        });
        
        // Top cap slice sector triangle
        panels.push({
          verts: [
            topRing[idx1],
            outerTop[next],
            topRing[idx2]
          ],
          color: '#4b4f5a', edge: '#4b4f5a', label: null
        });

        // Bottom cap slice sector quad
        panels.push({
          verts: [
            botRing[idx1],
            outerBot[next],
            outerBot[i],
            botRing[idx0]
          ],
          color: '#363941', edge: '#363941', label: null
        });
        
        // Bottom cap slice sector triangle
        panels.push({
          verts: [
            botRing[idx2],
            outerBot[next],
            botRing[idx1]
          ],
          color: '#363941', edge: '#363941', label: null
        });
      }

    } else if (setup === 'Washer') {
      const washerDiam = d * 2.0;
      const thick = Math.max(8.0, d * 0.15);
      const headR = washerDiam / 2;
      const segs = 10;

      const outerTop = [];
      const outerBot = [];
      const innerTop = [];
      const innerBot = [];
      for (let i = 0; i < segs; i++) {
        const theta = (i / segs) * Math.PI * 2;
        const ox = Math.cos(theta) * headR;
        const oy = Math.sin(theta) * headR;
        const ix = Math.cos(theta) * r;
        const iy = Math.sin(theta) * r;
        outerBot.push([ox, oy, 0]);
        outerTop.push([ox, oy, thick]);
        innerBot.push([ix, iy, 0]);
        innerTop.push([ix, iy, thick]);
      }

      // Outer sides
      for (let i = 0; i < segs; i++) {
        const next = (i + 1) % segs;
        panels.push({
          verts: [
            outerBot[i],
            outerBot[next],
            outerTop[next],
            outerTop[i]
          ],
          color: '#4e515a', edge: '#636772', label: i === 2 ? `Washer (M${nomDiam})` : null
        });
      }

      // Top washer ring
      for (let i = 0; i < segs; i++) {
        const next = (i + 1) % segs;
        panels.push({
          verts: [
            innerTop[i],
            outerTop[i],
            outerTop[next],
            innerTop[next]
          ],
          color: '#3d3f47', edge: '#4f525c', label: null
        });
      }

    } else if (setup === 'Bracket') {
      const w = d * 2.5;
      const t = Math.max(10.0, d * 0.2);
      const h = d * 3.0;
      const b = d * 3.0;
      const hw = w / 2;

      // Base plate
      panels.push({
        verts: [[-hw, t, t], [hw, t, t], [hw, t, b], [-hw, t, b]],
        color: '#3d3f47', edge: '#4f525c', label: 'Base'
      });
      panels.push({
        verts: [[-hw, 0, b], [hw, 0, b], [hw, 0, 0], [-hw, 0, 0]],
        color: '#202227', edge: '#2e3037', label: null
      });
      panels.push({
        verts: [[-hw, 0, b], [-hw, t, b], [hw, t, b], [hw, 0, b]],
        color: '#2b2c31', edge: '#383a41', label: null
      });

      // Upright mounting plate
      panels.push({
        verts: [[-hw, t, t], [hw, t, t], [hw, h, t], [-hw, h, t]],
        color: '#4e515a', edge: '#636772', label: `Bracket (t=${(nomDiam * 0.2).toFixed(1)}mm)`
      });
      panels.push({
        verts: [[-hw, 0, 0], [-hw, h, 0], [hw, h, 0], [hw, 0, 0]],
        color: '#1a1b1e', edge: '#25272c', label: null
      });
      panels.push({
        verts: [[-hw, h, 0], [-hw, h, t], [hw, h, t], [hw, h, 0]],
        color: '#5b5e69', edge: '#727685', label: null
      });
    }

    return { panels, lines };
  }

  // ── 3D Math helpers ──────────────────────────────────────────────────────

  function rotateX(v, a) {
    const [x, y, z] = v;
    return [x, y * Math.cos(a) - z * Math.sin(a), y * Math.sin(a) + z * Math.cos(a)];
  }
  function rotateY(v, a) {
    const [x, y, z] = v;
    return [x * Math.cos(a) + z * Math.sin(a), y, -x * Math.sin(a) + z * Math.cos(a)];
  }
  function project(v, cx, cy, fov, zoom, panX = 0, panY = 0) {
    const [x, y, z] = v;
    const scale = (fov / (fov + z)) * zoom;
    return [cx + x * scale + panX, cy - y * scale + panY, z];
  }
  function centroidZ(verts) {
    return verts.reduce((s, v) => s + v[2], 0) / verts.length;
  }
  function faceNormal(v0, v1, v2) {
    const ax = v1[0]-v0[0], ay = v1[1]-v0[1], az = v1[2]-v0[2];
    const bx = v2[0]-v0[0], by = v2[1]-v0[1], bz = v2[2]-v0[2];
    const nx = ay*bz - az*by, ny = az*bx - ax*bz, nz = ax*by - ay*bx;
    const len = Math.sqrt(nx*nx + ny*ny + nz*nz) || 1;
    return [nx/len, ny/len, nz/len];
  }
  function lerpColor(hex1, hex2, t) {
    const c1 = hexToRgb(hex1), c2 = hexToRgb(hex2);
    const r = Math.round(c1[0] + (c2[0]-c1[0]) * t);
    const g = Math.round(c1[1] + (c2[1]-c1[1]) * t);
    const b = Math.round(c1[2] + (c2[2]-c1[2]) * t);
    return `rgb(${r},${g},${b})`;
  }
  function hexToRgb(hex) {
    hex = hex.replace('#', '');
    if (hex.length === 3) hex = hex.split('').map(c=>c+c).join('');
    return [parseInt(hex.slice(0,2),16), parseInt(hex.slice(2,4),16), parseInt(hex.slice(4,6),16)];
  }

  // ── Main render function ─────────────────────────────────────────────────

  function render(canvas, state, geo) {
    const ctx = canvas.getContext('2d');
    const W = canvas.width, H = canvas.height;
    ctx.clearRect(0, 0, W, H);

    // Background
    ctx.fillStyle = '#0d0e12';
    ctx.fillRect(0, 0, W, H);

    // Grid
    ctx.strokeStyle = 'rgba(0,255,255,0.04)';
    ctx.lineWidth = 1;
    for (let x = 0; x < W; x += 20) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
    for (let y = 0; y < H; y += 20) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }

    const cx = W / 2, cy = H / 2;
    const fov = 350;
    const light = [0.4, 0.8, -0.4]; // normalised light direction

    // ── Transform & project each polygon ──
    const projected = geo.panels.map(p => {
      const pv = p.verts.map(v => {
        let rv = rotateY(v, state.yaw);
        rv = rotateX(rv, state.pitch);
        return project(rv, cx, cy, fov, state.zoom, state.panX || 0, state.panY || 0);
      });
      return { ...p, pv, z: centroidZ(pv) };
    });

    // Painter's algorithm: back-to-front
    projected.sort((a, b) => b.z - a.z);

    projected.forEach(p => {
      if (p.pv.length < 3) return;
      
      // Flat shading
      const n = faceNormal(p.pv[0], p.pv[1], p.pv[2]);
      const dot = Math.max(0, n[0]*light[0] + n[1]*light[1] + n[2]*light[2]);
      const shade = 0.3 + dot * 0.7;
      // Fill
      ctx.beginPath();
      ctx.moveTo(p.pv[0][0], p.pv[0][1]);
      p.pv.slice(1).forEach(v => ctx.lineTo(v[0], v[1]));
      ctx.closePath();
      ctx.fillStyle = lerpColor('#0d0e12', p.color, shade);
      ctx.fill();
      // Edge
      if (p.isThread && p.pv.length === 4) {
        // Draw horizontal ring edges only (v0->v1 and v2->v3), skipping vertical segment edges
        ctx.beginPath();
        ctx.moveTo(p.pv[0][0], p.pv[0][1]);
        ctx.lineTo(p.pv[1][0], p.pv[1][1]);
        ctx.moveTo(p.pv[2][0], p.pv[2][1]);
        ctx.lineTo(p.pv[3][0], p.pv[3][1]);
        ctx.strokeStyle = p.edge;
        ctx.lineWidth = 1.2;
        ctx.stroke();
      } else {
        ctx.strokeStyle = p.edge;
        ctx.lineWidth = 1.2;
        ctx.stroke();
      }

      // Label
      if (p.label) {
        const avgX = p.pv.reduce((s,v)=>s+v[0],0)/p.pv.length;
        const avgY = p.pv.reduce((s,v)=>s+v[1],0)/p.pv.length;
        ctx.fillStyle = '#ffffff';
        ctx.font = '10px monospace';
        ctx.textAlign = 'center';
        ctx.fillText(p.label, avgX, avgY - 6);
      }
    });

    // ── Airflow lines ──
    geo.lines.forEach(line => {
      if (!line.pts || line.pts.length < 2) return;
      const projPts = line.pts.map(v => {
        let rv = rotateY(v, state.yaw);
        rv = rotateX(rv, state.pitch);
        return project(rv, cx, cy, fov, state.zoom, state.panX || 0, state.panY || 0);
      });
      for (let i = 0; i < projPts.length - 1; i++) {
        const t = i / (projPts.length - 1);
        ctx.beginPath();
        ctx.moveTo(projPts[i][0], projPts[i][1]);
        ctx.lineTo(projPts[i+1][0], projPts[i+1][1]);
        ctx.strokeStyle = typeof line.color === 'function' ? line.color(t) : (t < 0.5 ? '#00ffff' : '#ff00ff');
        ctx.lineWidth = 1;
        ctx.globalAlpha = 0.55;
        ctx.setLineDash([5, 4]);
        ctx.stroke();
        ctx.setLineDash([]);
        
        // Draw little arrow heads indicating flow direction (every 4th segment)
        if (i % 4 === 2) {
          const dx = projPts[i+1][0] - projPts[i][0];
          const dy = projPts[i+1][1] - projPts[i][1];
          const angle = Math.atan2(dy, dx);
          
          ctx.beginPath();
          ctx.strokeStyle = typeof line.color === 'function' ? line.color(t) : (t < 0.5 ? '#00ffff' : '#ff00ff');
          ctx.lineWidth = 1.2;
          ctx.globalAlpha = 0.75;
          
          const size = 5;
          const ax = projPts[i+1][0] - dx / 2;
          const ay = projPts[i+1][1] - dy / 2;
          
          ctx.moveTo(ax - size * Math.cos(angle - Math.PI / 6), ay - size * Math.sin(angle - Math.PI / 6));
          ctx.lineTo(ax, ay);
          ctx.lineTo(ax - size * Math.cos(angle + Math.PI / 6), ay - size * Math.sin(angle + Math.PI / 6));
          ctx.stroke();
        }
        
        ctx.globalAlpha = 1;
      }
    });

    // ── HUD overlay ──
    ctx.fillStyle = 'rgba(0,255,255,0.07)';
    ctx.fillRect(0, 0, W, 30);
    ctx.fillStyle = '#00ffff';
    ctx.font = 'bold 11px monospace';
    ctx.textAlign = 'left';
    ctx.fillText(`F1 3D CAD VIEWER  |  Yaw: ${(state.yaw * 180 / Math.PI).toFixed(1)}°  Pitch: ${(state.pitch * 180 / Math.PI).toFixed(1)}°  Zoom: ${state.zoom.toFixed(2)}x`, 12, 20);
    ctx.textAlign = 'right';
    ctx.fillStyle = 'rgba(255,255,255,0.4)';
    ctx.font = '10px monospace';
    ctx.fillText('Drag to rotate  |  Scroll to zoom  |  Dbl-click to reset', W - 12, 20);
  }

  // ── OBJ export helper ────────────────────────────────────────────────────

  function generateOBJ(component, setup, nomDiam, length) {
    let geo;
    if (component === 'Fastener') {
      geo = getFastenerGeometry(setup, nomDiam || 8, length || 40);
    } else {
      geo = component === 'Front Wing' ? getFrontWingGeometry(setup)
          : component === 'Chassis Profile' ? getChassisGeometry(setup)
          : getRearWingGeometry(setup, false);
    }

    let obj = `# F1 CAD Export — ${component} (${setup})\n`;
    obj += `# Generated by F1 AI Assistant\n`;
    obj += `# Units: mm (scale 1:1)\n\n`;
    obj += `mtllib f1_cad.mtl\n\n`;

    let vIndex = 1;
    geo.panels.forEach((p, fi) => {
      obj += `o face_${fi}\n`;
      p.verts.forEach(v => { obj += `v ${v[0].toFixed(3)} ${v[1].toFixed(3)} ${v[2].toFixed(3)}\n`; });
      obj += `usemtl mat_${fi % 3}\n`;
      obj += `f`;
      for (let i = 0; i < p.verts.length; i++) obj += ` ${vIndex + i}`;
      obj += `\n`;
      vIndex += p.verts.length;
    });

    const mtl = `newmtl mat_0\nKd 0.26 0.28 0.32\nKs 0.4 0.4 0.4\nNs 50\n\n`
              + `newmtl mat_1\nKd 0.15 0.16 0.18\nKs 0.4 0.4 0.4\nNs 50\n\n`
              + `newmtl mat_2\nKd 0.30 0.30 0.32\nKs 0.2 0.2 0.2\nNs 20\n`;

    return { obj, mtl };
  }

  // ── Public initializer ────────────────────────────────────────────────────

  window.init3DBlueprints = function (container) {
    container = container || document;
    const holders = container.querySelectorAll('[data-cad3d]');
    holders.forEach(holder => {
      if (holder.dataset.cad3dInit) return; // already initialized
      holder.dataset.cad3dInit = '1';

      const component = holder.dataset.component || 'Rear Wing';
      const setup     = holder.dataset.setup     || 'Balanced';
      const nomDiam   = holder.dataset.dimDiam   ? parseFloat(holder.dataset.dimDiam) : 8.0;
      const length    = holder.dataset.dimLength ? parseFloat(holder.dataset.dimLength) : 40.0;

      let drsActive = false;
      function getGeo() {
        if (component === 'Fastener') {
          return getFastenerGeometry(setup, nomDiam, length);
        }
        if (component === 'Front Wing') return getFrontWingGeometry(setup);
        if (component === 'Chassis Profile') return getChassisGeometry(setup);
        return getRearWingGeometry(setup, drsActive);
      }

      let geo = getGeo();

      // Wrapper
      holder.style.cssText = 'position:relative; background:#0d0e12; border-radius:12px; border:1px solid rgba(0,255,255,0.2); overflow:hidden; margin:16px 0; box-shadow:0 10px 40px rgba(0,0,0,0.7);';

      // Canvas
      const canvas = document.createElement('canvas');
      canvas.width  = 720;
      canvas.height = 420;
      canvas.style.cssText = 'width:100%; height:auto; display:block; cursor:grab;';
      holder.appendChild(canvas);

      // Title bar
      const titleBar = document.createElement('div');
      titleBar.style.cssText = 'position:absolute; top:0; left:0; right:0; padding:8px 14px; background:rgba(13,14,18,0.85); border-bottom:1px solid rgba(0,255,255,0.15); display:flex; align-items:center; justify-content:space-between; z-index:10;';
      
      let titleText = `🔩 ${component.toUpperCase()}`;
      if (component === 'Fastener') {
        titleText += ` (${setup} — M${nomDiam} × ${length}mm)`;
      } else {
        titleText += ` — ${setup} | FIA 2026`;
      }
      
      titleBar.innerHTML = `<span style="color:#00ffff; font-family:monospace; font-size:12px; font-weight:bold;">${titleText}</span>`;
      holder.insertBefore(titleBar, canvas);

      // Control group
      const btnGroup = document.createElement('div');
      btnGroup.style.cssText = 'display:flex; gap:8px; align-items:center;';
      titleBar.appendChild(btnGroup);

      // DRS Toggle Button (Rear Wing only)
      if (component === 'Rear Wing') {
        const drsBtn = document.createElement('button');
        drsBtn.textContent = 'Toggle DRS [Closed]';
        drsBtn.style.cssText = 'background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.2); color:#ffffff; font-family:monospace; font-size:11px; padding:4px 12px; border-radius:6px; cursor:pointer; transition:all 0.2s;';
        drsBtn.onmouseenter = () => { drsBtn.style.background='rgba(255,255,255,0.1)'; };
        drsBtn.onmouseleave = () => { drsBtn.style.background='rgba(255,255,255,0.05)'; };
        drsBtn.onclick = () => {
          drsActive = !drsActive;
          drsBtn.textContent = `Toggle DRS [${drsActive ? 'OPEN' : 'Closed'}]`;
          drsBtn.style.borderColor = drsActive ? '#00ffff' : 'rgba(255,255,255,0.2)';
          drsBtn.style.color = drsActive ? '#00ffff' : '#ffffff';
          // Re-generate geometry and redraw
          geo = getGeo();
          draw();
        };
        btnGroup.appendChild(drsBtn);
      }

      // Zoom buttons (+ and -) for hardware safety/compatibility
      const zoomOutBtn = document.createElement('button');
      zoomOutBtn.textContent = ' ➖ ';
      zoomOutBtn.title = 'Zoom Out';
      zoomOutBtn.style.cssText = 'background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.2); color:#ffffff; font-family:monospace; font-size:11px; padding:4px 8px; border-radius:6px; cursor:pointer; transition:all 0.2s;';
      zoomOutBtn.onmouseenter = () => { zoomOutBtn.style.background='rgba(255,255,255,0.1)'; };
      zoomOutBtn.onmouseleave = () => { zoomOutBtn.style.background='rgba(255,255,255,0.05)'; };
      zoomOutBtn.onclick = (e) => {
        e.stopPropagation();
        state.zoom = Math.max(0.2, state.zoom - 0.2);
        draw();
      };
      btnGroup.appendChild(zoomOutBtn);

      const zoomInBtn = document.createElement('button');
      zoomInBtn.textContent = ' ➕ ';
      zoomInBtn.title = 'Zoom In';
      zoomInBtn.style.cssText = 'background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.2); color:#ffffff; font-family:monospace; font-size:11px; padding:4px 8px; border-radius:6px; cursor:pointer; transition:all 0.2s;';
      zoomInBtn.onmouseenter = () => { zoomInBtn.style.background='rgba(255,255,255,0.1)'; };
      zoomInBtn.onmouseleave = () => { zoomInBtn.style.background='rgba(255,255,255,0.05)'; };
      zoomInBtn.onclick = (e) => {
        e.stopPropagation();
        state.zoom = Math.min(15.0, state.zoom + 0.2);
        draw();
      };
      btnGroup.appendChild(zoomInBtn);

      // Download button
      const dlBtn = document.createElement('button');
      dlBtn.textContent = '⬇ Download OBJ';
      dlBtn.style.cssText = 'background:linear-gradient(135deg,#00ffff22,#ff005522); border:1px solid rgba(0,255,255,0.4); color:#00ffff; font-family:monospace; font-size:11px; padding:4px 12px; border-radius:6px; cursor:pointer; transition:all 0.2s;';
      dlBtn.onmouseenter = () => { dlBtn.style.background='linear-gradient(135deg,#00ffff44,#ff005544)'; };
      dlBtn.onmouseleave = () => { dlBtn.style.background='linear-gradient(135deg,#00ffff22,#ff005522)'; };
      dlBtn.onclick = () => {
        const { obj, mtl } = generateOBJ(component, setup, nomDiam, length);
        const slug = component.replace(/\s+/g, '_').toLowerCase();

        // Download .obj
        const a1 = document.createElement('a');
        a1.href = 'data:text/plain;charset=utf-8,' + encodeURIComponent(obj);
        a1.download = `f1_${slug}_${setup.replace(/\s+/g,'_').toLowerCase()}.obj`;
        a1.click();

        // Download .mtl after short delay
        setTimeout(() => {
          const a2 = document.createElement('a');
          a2.href = 'data:text/plain;charset=utf-8,' + encodeURIComponent(mtl);
          a2.download = 'f1_cad.mtl';
          a2.click();
        }, 400);
      };
      btnGroup.appendChild(dlBtn);

      // Info bar (spec summary)
      const infoBar = document.createElement('div');
      infoBar.style.cssText = 'padding:6px 14px; background:rgba(0,0,0,0.4); border-top:1px solid rgba(0,255,255,0.08); font-family:monospace; font-size:10px; color:#a0aab2; display:flex; gap:20px;';

      let specs;
      if (component === 'Fastener') {
        specs = [
          ['Type', setup],
          ['Diameter', `M${nomDiam}`],
          ['Length', `${length} mm`],
          ['Standard', setup === 'Bolt' ? 'DIN 912' : (setup === 'Nut' ? 'ISO 4032' : 'ISO 7089')]
        ];
      } else if (component === 'Rear Wing') {
        specs = [['Span','850 mm'],['DRS Gap','85 mm'],['Status','FIA ✓']];
      } else if (component === 'Front Wing') {
        specs = [['Span','1950 mm'],['Elements','4 Flaps'],['Status','FIA ✓']];
      } else {
        specs = [['Wheelbase','3400 mm'],['Width','1900 mm'],['Status','FIA ✓']];
      }
      specs.forEach(([k,v]) => {
        const d = document.createElement('div');
        d.innerHTML = `${k}: <span style="color:#00ffff">${v}</span>`;
        infoBar.appendChild(d);
      });
      holder.appendChild(infoBar);

      // State
      const state = { yaw: -0.4, pitch: 0.22, zoom: 1.0, dragging: false, lastX: 0, lastY: 0, panX: 0, panY: 0 };

      function draw() { render(canvas, state, geo); }
      draw();

      // Prevent canvas right-click context menu to allow seamless right-click panning
      canvas.addEventListener('contextmenu', e => e.preventDefault());

      // ── Drag to rotate / Shift or Right-Click to pan ──
      canvas.addEventListener('mousedown', e => {
        state.dragging = true;
        // Shift key, Ctrl key, or Right Mouse Button triggers pan translation mode
        state.isPanning = (e.shiftKey || e.ctrlKey || e.button === 2);
        state.lastX = e.clientX;
        state.lastY = e.clientY;
        canvas.style.cursor = state.isPanning ? 'move' : 'grabbing';
        e.preventDefault();
      });

      window.addEventListener('mousemove', e => {
        if (!state.dragging) return;
        const dx = e.clientX - state.lastX;
        const dy = e.clientY - state.lastY;
        
        if (state.isPanning) {
          state.panX += dx;
          state.panY += dy;
        } else {
          state.yaw   += dx * 0.008;
          state.pitch += dy * 0.008;
          state.pitch = Math.max(-1.4, Math.min(1.4, state.pitch));
        }
        
        state.lastX = e.clientX;
        state.lastY = e.clientY;
        draw();
      });

      window.addEventListener('mouseup', () => {
        state.dragging = false;
        canvas.style.cursor = 'grab';
      });

      // ── Touch drag, pinch-to-zoom and two-finger touch pan ──
      canvas.addEventListener('touchstart', e => {
        if (e.touches.length === 1) {
          state.dragging = true;
          state.isPinching = false;
          state.lastX = e.touches[0].clientX;
          state.lastY = e.touches[0].clientY;
        } else if (e.touches.length === 2) {
          state.dragging = false;
          state.isPinching = true;
          
          // Distance for zooming
          const dx = e.touches[0].clientX - e.touches[1].clientX;
          const dy = e.touches[0].clientY - e.touches[1].clientY;
          state.startTouchDist = Math.sqrt(dx * dx + dy * dy) || 1;
          state.startZoom = state.zoom;
          
          // Midpoint for panning
          state.lastMidX = (e.touches[0].clientX + e.touches[1].clientX) / 2;
          state.lastMidY = (e.touches[0].clientY + e.touches[1].clientY) / 2;
        }
        e.preventDefault();
      }, { passive: false });

      canvas.addEventListener('touchmove', e => {
        if (state.dragging && e.touches.length === 1) {
          const dx = e.touches[0].clientX - state.lastX;
          const dy = e.touches[0].clientY - state.lastY;
          state.yaw   += dx * 0.008;
          state.pitch += dy * 0.008;
          state.pitch = Math.max(-1.4, Math.min(1.4, state.pitch));
          state.lastX = e.touches[0].clientX;
          state.lastY = e.touches[0].clientY;
          draw();
        } else if (state.isPinching && e.touches.length === 2) {
          // 1. Zoom
          const dx = e.touches[0].clientX - e.touches[1].clientX;
          const dy = e.touches[0].clientY - e.touches[1].clientY;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const ratio = dist / state.startTouchDist;
          state.zoom = Math.max(0.2, Math.min(15.0, state.startZoom * ratio));
          
          // 2. Pan
          const midX = (e.touches[0].clientX + e.touches[1].clientX) / 2;
          const midY = (e.touches[0].clientY + e.touches[1].clientY) / 2;
          const dMidX = midX - state.lastMidX;
          const dMidY = midY - state.lastMidY;
          state.panX += dMidX;
          state.panY += dMidY;
          state.lastMidX = midX;
          state.lastMidY = midY;
          
          draw();
        }
        e.preventDefault();
      }, { passive: false });

      canvas.addEventListener('touchend', () => {
        state.dragging = false;
        state.isPinching = false;
      });

      // ── Scroll to zoom ──
      canvas.addEventListener('wheel', e => {
        state.zoom = Math.max(0.2, Math.min(15.0, state.zoom - e.deltaY * 0.0015));
        draw();
        e.preventDefault();
      }, { passive: false });

      // ── Double-click reset ──
      canvas.addEventListener('dblclick', () => {
        state.yaw = -0.4; state.pitch = 0.22; state.zoom = 1.0;
        state.panX = 0; state.panY = 0;
        draw();
      });
    });
  };

})();
