"""
Custom Pipecat Frame Processors
Implements behavioral reward processing and action coordination
"""

import logging
from typing import Optional

from pipecat.frames.frames import Frame, StartFrame, EndFrame, CancelFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

logger = logging.getLogger(__name__)

# ============================================
# CUSTOM ACTION FRAMES
# ============================================

class ActionFrame(Frame):
    """Frame carrying coordinate-based action instructions for Electron"""
    def __init__(self, action: str, start_pos: dict, end_pos: dict, metadata: Optional[dict] = None):
        super().__init__()
        self.action = action
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.metadata = metadata or {}

class ActionFeedbackFrame(Frame):
    """Frame carrying feedback from Electron about an action success"""
    def __init__(self, action_id: str, success: bool, user_delta: float, metadata: Optional[dict] = None):
        super().__init__()
        self.action_id = action_id
        self.success = success
        self.user_delta = user_delta
        self.metadata = metadata or {}

# ============================================
class RewardProcessor(FrameProcessor):
    """
    Observes ActionFeedbackFrames and updates the reward store.
    This acts as the Behavioral Learning hook in the pipeline.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """Process incoming frames to detect feedback and update rewards"""
        
        # Let parent class handle lifecycle frames
        if isinstance(frame, (StartFrame, EndFrame, CancelFrame)):
            await self.push_frame(frame, direction)
            return
        
        # Process ActionFeedbackFrame if applicable
        if isinstance(frame, ActionFeedbackFrame):
            logger.info(f"Received feedback for action {frame.action_id}: success={frame.success}")
            
            # Calculate reward based on success and user delta (distance to target)
            reward = 1.0 if frame.success and frame.user_delta < 50 else -1.0
            
            # Update Episodic Memory / Reward Store
            await self._update_reward_store(frame.action_id, reward, frame.metadata)
        
        # Pass all frames downstream
        await self.push_frame(frame, direction)

    async def _update_reward_store(self, action_id: str, reward: float, metadata: dict):
        """
        Updates the Redis-style Episodic Memory.
        The RL logic uses a composite key of (Screen + Intent) to store mask success.
        """
        screen_hash = metadata.get("screen_state_hash")  # The 'State'
        intent = metadata.get("user_intent")            # The 'Action'
        mask_id = metadata.get("sam_mask_id")           # The 'Specific Actuator'
        
        if not (screen_hash and intent and mask_id):
            logger.warning(f"Missing RL metadata for action {action_id}")
            return

        # Store reward in Redis using the bridge
        try:
            from app.redis_client import store_reward
            success = store_reward(screen_hash, intent, mask_id, reward)
            
            if success:
                logger.info(f"✓ RL STORED: Screen={screen_hash[:8]}, Intent={intent}, Mask={mask_id}, Reward={reward}")
            else:
                logger.info(f"RL FALLBACK (Redis unavailable): Mask={mask_id}, Reward={reward}")
        except ImportError:
            logger.debug(f"Redis not available - RL reward not stored: {action_id}")
