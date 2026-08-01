import React from 'react';
import { BaseEdge, EdgeLabelRenderer } from '@xyflow/react';
import type { EdgeProps } from '@xyflow/react';

export const LoopEdge: React.FC<EdgeProps> = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  label,
  style,
  markerEnd
}) => {
  const radius = 24;

  // Route above: go up from source, across to target, then down
  const minY = Math.min(sourceY, targetY);
  const laneY = minY - 80; // lane runs above both nodes

  const path = [
    `M ${sourceX} ${sourceY}`,
    `L ${sourceX} ${laneY + radius}`,
    `Q ${sourceX} ${laneY} ${sourceX + (targetX < sourceX ? -radius : radius)} ${laneY}`,
    `L ${targetX + (targetX < sourceX ? radius : -radius)} ${laneY}`,
    `Q ${targetX} ${laneY} ${targetX} ${laneY + radius}`,
    `L ${targetX} ${targetY}`
  ].join(' ');

  const labelX = (sourceX + targetX) / 2;
  const labelY = laneY - 12;
  const labelColor = style?.stroke || '#1e293b';

  return (
    <>
      <BaseEdge id={id} path={path} style={{ ...style, strokeWidth: 2 }} markerEnd={markerEnd} />
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
