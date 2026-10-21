import St from 'gi://St';
import Clutter from 'gi://Clutter';
import {color} from './ui.js';

export function createGraph() {
    return new St.DrawingArea({style_class: 'gpt-usage-graph', y_align: Clutter.ActorAlign.CENTER});
}

export function paintGraph(area, values, mode, remaining) {
    const cr = area.get_context();
    try {
        const [width, height] = area.get_surface_size();
        for (let i = 0; i < 2; i++) {
            const value = values[i];
            cr.setSourceRGBA(0.5, 0.55, 0.6, 0.28);
            if (mode === 'bars') {
                const y = 3 + i * 9;
                cr.rectangle(1, y, width - 2, 5);
                cr.fill();
                cr.setSourceRGB(...color(value, remaining));
                if (value !== null) {
                    cr.rectangle(1, y, (width - 2) * value / 100, 5);
                    cr.fill();
                } else {
                    cr.moveTo(width / 2 - 3, y + 2.5);
                    cr.lineTo(width / 2 + 3, y + 2.5);
                    cr.stroke();
                }
            } else {
                const x = width * (i === 0 ? 0.25 : 0.75);
                const y = height / 2;
                const radius = Math.min(width / 4 - 2, height / 2 - 3);
                cr.setLineWidth(3);
                cr.arc(x, y, radius, 0, 2 * Math.PI);
                cr.stroke();
                cr.setSourceRGB(...color(value, remaining));
                if (value !== null && value > 0) {
                    cr.arc(x, y, radius, -Math.PI / 2, -Math.PI / 2 + 2 * Math.PI * value / 100);
                    cr.stroke();
                } else if (value === null) {
                    cr.moveTo(x - 3, y);
                    cr.lineTo(x + 3, y);
                    cr.stroke();
                }
            }
        }
    } finally {
        cr.$dispose();
    }
}
