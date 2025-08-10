"""AWS Bedrock client for LLM-powered trading decisions."""

import json
import boto3
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import structlog
from botocore.exceptions import ClientError, BotoCoreError

from ..core.config import BedrockConfig

logger = structlog.get_logger(__name__)


class BedrockClient:
    """Client for interacting with AWS Bedrock models."""
    
    def __init__(self, config: BedrockConfig):
        self.config = config
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Bedrock client with proper credentials."""
        try:
            session_kwargs = {"region_name": self.config.region}
            
            # Use profile if specified
            if self.config.aws_profile:
                session = boto3.Session(profile_name=self.config.aws_profile)
                self.client = session.client("bedrock-runtime", **session_kwargs)
            else:
                # Use environment variables or IAM role
                self.client = boto3.client("bedrock-runtime", **session_kwargs)
            
            logger.info("Bedrock client initialized successfully", region=self.config.region)
            
        except Exception as e:
            logger.error("Failed to initialize Bedrock client", error=str(e))
            raise
    
    async def analyze_market_conditions(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze current market conditions and provide trading insights."""
        prompt = self._build_market_analysis_prompt(market_data)
        
        response = await self._invoke_model(prompt, "market_analysis")
        return self._parse_market_analysis_response(response)
    
    async def make_trading_decision(
        self, 
        market_data: Dict[str, Any], 
        news_data: Dict[str, Any],
        portfolio_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Make a trading decision based on market data, news, and portfolio."""
        prompt = self._build_trading_decision_prompt(market_data, news_data, portfolio_data)
        
        response = await self._invoke_model(prompt, "trading_decision")
        return self._parse_trading_decision_response(response)
    
    async def evaluate_position(
        self, 
        position_data: Dict[str, Any], 
        market_data: Dict[str, Any],
        news_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Evaluate current position and decide on next actions."""
        prompt = self._build_position_evaluation_prompt(position_data, market_data, news_data)
        
        response = await self._invoke_model(prompt, "position_evaluation")
        return self._parse_position_evaluation_response(response)
    
    async def determine_position_size(
        self, 
        available_balance: float, 
        market_conditions: Dict[str, Any],
        risk_assessment: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Determine optimal position size based on risk and market conditions."""
        prompt = self._build_position_sizing_prompt(available_balance, market_conditions, risk_assessment)
        
        response = await self._invoke_model(prompt, "position_sizing")
        return self._parse_position_sizing_response(response)
    
    async def _invoke_model(self, prompt: str, operation_type: str) -> str:
        """Invoke the Bedrock model with the given prompt."""
        try:
            # Prepare the request body for Claude
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            # Try primary model first
            try:
                response = self.client.invoke_model(
                    modelId=self.config.model_id,
                    body=json.dumps(body)
                )
                model_used = self.config.model_id
            except ClientError as e:
                logger.warning(
                    "Primary model failed, trying fallback", 
                    primary_model=self.config.model_id,
                    error=str(e)
                )
                # Try fallback model
                response = self.client.invoke_model(
                    modelId=self.config.fallback_model_id,
                    body=json.dumps(body)
                )
                model_used = self.config.fallback_model_id
            
            # Parse response
            response_body = json.loads(response['body'].read())
            content = response_body['content'][0]['text']
            
            logger.info(
                "LLM response received",
                operation_type=operation_type,
                model_used=model_used,
                response_length=len(content)
            )
            
            return content
            
        except Exception as e:
            logger.error(
                "Failed to invoke Bedrock model",
                operation_type=operation_type,
                error=str(e)
            )
            raise
    
    def _build_market_analysis_prompt(self, market_data: Dict[str, Any]) -> str:
        """Build prompt for market analysis."""
        return f"""
You are an expert cryptocurrency market analyst. Analyze the current market conditions and provide insights.

Market Data:
{json.dumps(market_data, indent=2)}

Please provide a comprehensive market analysis including:

1. **Market Trend**: Current trend direction (bullish, bearish, sideways)
2. **Volatility Assessment**: Current volatility level and implications
3. **Support/Resistance Levels**: Key technical levels
4. **Market Sentiment**: Overall market sentiment
5. **Risk Level**: Current market risk assessment (low, medium, high)
6. **Trading Opportunities**: Potential trading setups
7. **Recommended Strategy**: Best strategy for current conditions

Format your response as JSON with the following structure:
{{
    "trend": "bullish|bearish|sideways",
    "volatility": "low|medium|high",
    "sentiment": "very_bearish|bearish|neutral|bullish|very_bullish",
    "risk_level": "low|medium|high",
    "support_levels": [price1, price2],
    "resistance_levels": [price1, price2],
    "recommended_strategy": "trend_following|mean_reversion|breakout|range_trading",
    "confidence": 0.0-1.0,
    "reasoning": "detailed explanation of analysis"
}}
"""
    
    def _build_trading_decision_prompt(
        self, 
        market_data: Dict[str, Any], 
        news_data: Dict[str, Any],
        portfolio_data: Dict[str, Any]
    ) -> str:
        """Build prompt for trading decisions."""
        return f"""
You are an expert cryptocurrency trader making trading decisions. Based on the provided data, decide whether to enter a trade.

Market Data:
{json.dumps(market_data, indent=2)}

News Data:
{json.dumps(news_data, indent=2)}

Portfolio Data:
{json.dumps(portfolio_data, indent=2)}

Available position sizes: 5%, 10%, 15%, 20%, 25% of available balance.

Please make a trading decision considering:
1. Market conditions and technical analysis
2. News sentiment and fundamental factors
3. Risk management principles
4. Portfolio balance and exposure

Format your response as JSON:
{{
    "action": "buy|sell|hold",
    "symbol": "trading pair symbol",
    "position_size_percent": 5|10|15|20|25,
    "entry_price_target": "target entry price",
    "stop_loss": "stop loss price",
    "take_profit": "take profit price",
    "confidence": 0.0-1.0,
    "reasoning": "detailed explanation of decision",
    "risk_assessment": "low|medium|high",
    "expected_duration": "minutes|hours|days"
}}

If no good trading opportunity exists, set action to "hold" and explain why.
"""
    
    def _build_position_evaluation_prompt(
        self, 
        position_data: Dict[str, Any], 
        market_data: Dict[str, Any],
        news_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build prompt for position evaluation."""
        news_section = f"\nNews Data:\n{json.dumps(news_data, indent=2)}" if news_data else ""
        
        return f"""
You are managing an active cryptocurrency position. Evaluate the current position and decide on the next action.

Current Position:
{json.dumps(position_data, indent=2)}

Market Data:
{json.dumps(market_data, indent=2)}{news_section}

Please evaluate the position considering:
1. Current profit/loss status
2. Market conditions changes
3. Technical levels (support/resistance)
4. News impact (if any)
5. Risk management rules

Format your response as JSON:
{{
    "action": "hold|close|adjust_stop|adjust_target",
    "reasoning": "detailed explanation",
    "urgency": "low|medium|high",
    "new_stop_loss": "new stop loss price (if adjusting)",
    "new_take_profit": "new take profit price (if adjusting)",
    "confidence": 0.0-1.0,
    "risk_level": "low|medium|high"
}}
"""
    
    def _build_position_sizing_prompt(
        self, 
        available_balance: float, 
        market_conditions: Dict[str, Any],
        risk_assessment: Dict[str, Any]
    ) -> str:
        """Build prompt for position sizing."""
        return f"""
You are determining the optimal position size for a cryptocurrency trade.

Available Balance: ${available_balance:.2f}
Market Conditions: {json.dumps(market_conditions, indent=2)}
Risk Assessment: {json.dumps(risk_assessment, indent=2)}

Available position sizes: 5%, 10%, 15%, 20%, 25% of available balance.

Consider:
1. Market volatility
2. Risk level of the trade
3. Market conditions
4. Portfolio risk management

Format your response as JSON:
{{
    "position_size_percent": 5|10|15|20|25,
    "reasoning": "explanation for chosen size",
    "risk_justification": "why this size is appropriate for current risk",
    "confidence": 0.0-1.0
}}
"""
    
    def _parse_market_analysis_response(self, response: str) -> Dict[str, Any]:
        """Parse market analysis response from LLM."""
        try:
            # Try to extract JSON from response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx]
                return json.loads(json_str)
            else:
                # Fallback parsing
                return {
                    "trend": "neutral",
                    "volatility": "medium",
                    "sentiment": "neutral",
                    "risk_level": "medium",
                    "confidence": 0.5,
                    "reasoning": response
                }
        except json.JSONDecodeError:
            logger.warning("Failed to parse market analysis response as JSON")
            return {
                "trend": "neutral",
                "volatility": "medium", 
                "sentiment": "neutral",
                "risk_level": "medium",
                "confidence": 0.5,
                "reasoning": response
            }
    
    def _parse_trading_decision_response(self, response: str) -> Dict[str, Any]:
        """Parse trading decision response from LLM."""
        try:
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx]
                return json.loads(json_str)
            else:
                return {
                    "action": "hold",
                    "reasoning": response,
                    "confidence": 0.5
                }
        except json.JSONDecodeError:
            logger.warning("Failed to parse trading decision response as JSON")
            return {
                "action": "hold",
                "reasoning": response,
                "confidence": 0.5
            }
    
    def _parse_position_evaluation_response(self, response: str) -> Dict[str, Any]:
        """Parse position evaluation response from LLM."""
        try:
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx]
                return json.loads(json_str)
            else:
                return {
                    "action": "hold",
                    "reasoning": response,
                    "confidence": 0.5,
                    "urgency": "low"
                }
        except json.JSONDecodeError:
            logger.warning("Failed to parse position evaluation response as JSON")
            return {
                "action": "hold",
                "reasoning": response,
                "confidence": 0.5,
                "urgency": "low"
            }
    
    def _parse_position_sizing_response(self, response: str) -> Dict[str, Any]:
        """Parse position sizing response from LLM."""
        try:
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx]
                return json.loads(json_str)
            else:
                return {
                    "position_size_percent": 10,
                    "reasoning": response,
                    "confidence": 0.5
                }
        except json.JSONDecodeError:
            logger.warning("Failed to parse position sizing response as JSON")
            return {
                "position_size_percent": 10,
                "reasoning": response,
                "confidence": 0.5
            }
