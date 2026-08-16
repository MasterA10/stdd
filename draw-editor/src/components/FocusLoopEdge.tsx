import React from 'react';
import { BaseEdge, EdgeLabelRenderer } from '@xyflow/react';
import type { EdgeProps } from '@xyflow/react';

/** Desenha retornos do modo foco com segmentos retos fora dos blocos. */
export const FocusLoopEdge: React.FC<EdgeProps> = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  targetHandleId,
  label,
  style,
  markerEnd,
  data
}) => {
  const goesBelow = targetHandleId?.endsWith('bottom');
  const laneY = goesBelow
    ? Math.max(sourceY, targetY) + 72
    : Math.min(sourceY, targetY) - 72;
  const path = `M ${sourceX} ${sourceY} L ${sourceX} ${laneY} L ${targetX} ${laneY} L ${targetX} ${targetY}`;
  const labelX = (sourceX + targetX) / 2;
  const labelY = laneY - 12;
  const edgeData = data as { labelColor?: string } | undefined;
  const labelColor = edgeData?.labelColor || '#1e293b';

  return (
    <>
      <BaseEdge id={id} path={path} style={{ ...style, strokeWidth: 3 }} markerEnd={markerEnd} />
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
