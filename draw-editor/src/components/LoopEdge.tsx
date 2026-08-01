import React from 'react';
import { BaseEdge, EdgeLabelRenderer, useNodes } from '@xyflow/react';
import type { EdgeProps } from '@xyflow/react';

export const LoopEdge: React.FC<EdgeProps> = ({
  id,
  source,
  target,
  sourceX,
  sourceY,
  targetX,
  targetY,
  label,
  style,
  targetHandleId
}) => {
  const nodes = useNodes();
  const PAD = 24;
  const sourceNode = nodes.find(node => node.id === String(source));
  const targetNode = nodes.find(node => node.id === String(target));
  const otherBoxes = nodes
    .filter(node => node.id !== String(source) && node.id !== String(target))
    .map(node => ({
      left: node.position.x - PAD,
      right: node.position.x + (node.measured?.width || 290) + PAD,
      top: node.position.y - PAD,
      bottom: node.position.y + (node.measured?.height || 160) + PAD
    }));

  const minNodeY = Math.min(sourceNode?.position.y ?? sourceY, targetNode?.position.y ?? targetY);
  const maxNodeY = Math.max(
    (sourceNode?.position.y ?? sourceY) + (sourceNode?.measured?.height || 160),
    (targetNode?.position.y ?? targetY) + (targetNode?.measured?.height || 160)
  );
  const topLane = minNodeY - 80;
  const bottomLane = maxNodeY + 80;
  const targetSide = targetHandleId?.endsWith('bottom') ? 'bottom' : 'top';
  const lanes = targetSide === 'bottom'
    ? [{ side: 'bottom', y: bottomLane }, { side: 'top', y: topLane }]
    : [{ side: 'top', y: topLane }, { side: 'bottom', y: bottomLane }];

  const intersects = (x1: number, y1: number, x2: number, y2: number, box: typeof otherBoxes[number]) => {
    if (x1 === x2) return x1 > box.left && x1 < box.right && Math.min(y1, y2) < box.bottom && Math.max(y1, y2) > box.top;
    if (y1 === y2) return y1 > box.top && y1 < box.bottom && Math.min(x1, x2) < box.right && Math.max(x1, x2) > box.left;
    return false;
  };

  const laneRoutes = lanes.map((lane, order) => {
    const points = [
      { x: sourceX, y: sourceY },
      { x: sourceX, y: lane.y },
      { x: targetX, y: lane.y },
      { x: targetX, y: targetY }
    ];
    let intersections = 0;
    for (let index = 0; index < points.length - 1; index += 1) {
      intersections += otherBoxes.filter(box => intersects(
        points[index].x,
        points[index].y,
        points[index + 1].x,
        points[index + 1].y,
        box
      )).length;
    }
    let length = 0;
    for (let index = 0; index < points.length - 1; index += 1) {
      length += Math.abs(points[index + 1].x - points[index].x) + Math.abs(points[index + 1].y - points[index].y);
    }
    return { points, intersections, length, order, lane };
  });
  const route = laneRoutes.sort((a, b) => a.intersections - b.intersections || a.order - b.order || a.length - b.length)[0];

  const approach = targetSide === 'bottom' ? { x: 0, y: 1 } : { x: 0, y: -1 };
  const arrowTip = { x: targetX + approach.x * 12, y: targetY + approach.y * 12 };
  const arrowBase = { x: targetX + approach.x * 26, y: targetY + approach.y * 26 };
  const arrowHalfWidth = 8;
  const arrowPath = targetSide === 'bottom'
    ? `M ${arrowTip.x} ${arrowTip.y} L ${arrowBase.x - arrowHalfWidth} ${arrowBase.y} L ${arrowBase.x + arrowHalfWidth} ${arrowBase.y} Z`
    : `M ${arrowTip.x} ${arrowTip.y} L ${arrowBase.x - arrowHalfWidth} ${arrowBase.y} L ${arrowBase.x + arrowHalfWidth} ${arrowBase.y} Z`;

  const visiblePoints = [...route.points.slice(0, -1), arrowTip];
  const path = visiblePoints.map((point, index) => {
    if (index === 0) return `M ${point.x} ${point.y}`;
    return `L ${point.x} ${point.y}`;
  }).join(' ');

  const labelX = (sourceX + targetX) / 2;
  const labelY = route.lane.y - 12;
  const labelColor = style?.stroke || '#1e293b';

  return (
    <>
      <BaseEdge id={id} path={path} style={{ ...style, strokeWidth: 2 }} />
      <path d={arrowPath} fill={labelColor} stroke={labelColor} strokeWidth="1" strokeLinejoin="round" />
      {label && (
        <EdgeLabelRenderer>
          <div
            className="loop-edge-label"
            style={{
              color: labelColor,
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
              position: 'absolute',
              pointerEvents: 'all'
            }}
          >
            {label}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
};
