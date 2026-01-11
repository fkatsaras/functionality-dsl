#!/usr/bin/env python3
"""
Generate an Ecore metamodel from FDSL textX grammar.

This script creates an .ecore file that represents the FDSL core metamodel,
suitable for use in Eclipse EMF tools.

Usage:
    python scripts/generate_ecore.py [--output path/to/output.ecore]
"""

import argparse
from pathlib import Path

from pyecore.ecore import (
    EPackage, EClass, EAttribute, EReference, EEnum, EEnumLiteral,
    EString, EInt, EFloat, EBoolean
)
from pyecore.resources import ResourceSet, URI


def create_fdsl_metamodel():
    """Create the FDSL Ecore metamodel (core classes only, no Components)."""

    # Root package
    fdsl = EPackage('fdsl', nsURI='http://fdsl.io/metamodel/1.0', nsPrefix='fdsl')

    # ==========================================================================
    # Enumerations
    # ==========================================================================

    # AttrType enum
    AttrType = EEnum('AttrType')
    for val in ['string', 'integer', 'number', 'boolean', 'array', 'object', 'binary']:
        AttrType.eLiterals.append(EEnumLiteral(val.upper(), value=len(AttrType.eLiterals)))
    fdsl.eClassifiers.append(AttrType)

    # TypeFormat enum
    TypeFormat = EEnum('TypeFormat')
    for val in ['email', 'uri', 'uuid_str', 'date', 'time', 'hostname', 'ipv4', 'ipv6',
                'byte', 'binary', 'password', 'regex', 'float', 'double', 'int32', 'int64']:
        TypeFormat.eLiterals.append(EEnumLiteral(val.upper(), value=len(TypeFormat.eLiterals)))
    fdsl.eClassifiers.append(TypeFormat)

    # Operation enum
    Operation = EEnum('Operation')
    for val in ['read', 'create', 'update', 'delete', 'subscribe', 'publish']:
        Operation.eLiterals.append(EEnumLiteral(val.upper(), value=len(Operation.eLiterals)))
    fdsl.eClassifiers.append(Operation)

    # AuthType enum
    AuthType = EEnum('AuthType')
    for val in ['jwt', 'session']:
        AuthType.eLiterals.append(EEnumLiteral(val.upper(), value=len(AuthType.eLiterals)))
    fdsl.eClassifiers.append(AuthType)

    # WSFlowType enum
    WSFlowType = EEnum('WSFlowType')
    for val in ['inbound', 'outbound']:
        WSFlowType.eLiterals.append(EEnumLiteral(val.upper(), value=len(WSFlowType.eLiterals)))
    fdsl.eClassifiers.append(WSFlowType)

    # ==========================================================================
    # Core Model Classes
    # ==========================================================================

    # FDSLModel - Root class
    FDSLModel = EClass('FDSLModel')
    fdsl.eClassifiers.append(FDSLModel)

    # Import
    Import = EClass('Import')
    Import.eStructuralFeatures.append(EAttribute('importURI', EString))
    fdsl.eClassifiers.append(Import)

    # ==========================================================================
    # RBAC Classes
    # ==========================================================================

    # Role
    Role = EClass('Role')
    Role.eStructuralFeatures.append(EAttribute('name', EString))
    fdsl.eClassifiers.append(Role)

    # AccessBlock (abstract)
    AccessBlock = EClass('AccessBlock', abstract=True)
    fdsl.eClassifiers.append(AccessBlock)

    # PublicAccess
    PublicAccess = EClass('PublicAccess')
    PublicAccess.eSuperTypes.append(AccessBlock)
    fdsl.eClassifiers.append(PublicAccess)

    # RoleBasedAccess
    RoleBasedAccess = EClass('RoleBasedAccess')
    RoleBasedAccess.eSuperTypes.append(AccessBlock)
    fdsl.eClassifiers.append(RoleBasedAccess)

    # PerOperationAccess
    PerOperationAccess = EClass('PerOperationAccess')
    PerOperationAccess.eSuperTypes.append(AccessBlock)
    fdsl.eClassifiers.append(PerOperationAccess)

    # AccessRule
    AccessRule = EClass('AccessRule')
    AccessRule.eStructuralFeatures.append(EAttribute('operation', Operation))
    AccessRule.eStructuralFeatures.append(EAttribute('isPublic', EBoolean))
    fdsl.eClassifiers.append(AccessRule)

    # ==========================================================================
    # Auth Classes
    # ==========================================================================

    # Auth
    Auth = EClass('Auth')
    Auth.eStructuralFeatures.append(EAttribute('name', EString))
    Auth.eStructuralFeatures.append(EAttribute('type', AuthType))
    fdsl.eClassifiers.append(Auth)

    # JWTAuthConfig
    # secret: environment variable name for JWT secret
    JWTAuthConfig = EClass('JWTAuthConfig')
    JWTAuthConfig.eStructuralFeatures.append(EAttribute('secret', EString))
    JWTAuthConfig.eStructuralFeatures.append(EAttribute('header', EString))
    JWTAuthConfig.eStructuralFeatures.append(EAttribute('scheme', EString))
    JWTAuthConfig.eStructuralFeatures.append(EAttribute('algorithm', EString))
    JWTAuthConfig.eStructuralFeatures.append(EAttribute('user_id_claim', EString))
    JWTAuthConfig.eStructuralFeatures.append(EAttribute('roles_claim', EString))
    fdsl.eClassifiers.append(JWTAuthConfig)

    # SessionAuthConfig
    SessionAuthConfig = EClass('SessionAuthConfig')
    SessionAuthConfig.eStructuralFeatures.append(EAttribute('cookie', EString))
    SessionAuthConfig.eStructuralFeatures.append(EAttribute('expiry', EInt))
    fdsl.eClassifiers.append(SessionAuthConfig)

    # ==========================================================================
    # Server Classes
    # ==========================================================================

    # Server
    Server = EClass('Server')
    Server.eStructuralFeatures.append(EAttribute('name', EString))
    Server.eStructuralFeatures.append(EAttribute('host', EString))
    Server.eStructuralFeatures.append(EAttribute('port', EInt))
    Server.eStructuralFeatures.append(EAttribute('base', EString))
    Server.eStructuralFeatures.append(EAttribute('cors', EString, upper=-1))
    Server.eStructuralFeatures.append(EAttribute('env', EString))
    Server.eStructuralFeatures.append(EAttribute('loglevel', EString))
    Server.eStructuralFeatures.append(EAttribute('timeout', EInt))
    fdsl.eClassifiers.append(Server)

    # ==========================================================================
    # Source Classes
    # ==========================================================================

    # Source (abstract)
    Source = EClass('Source', abstract=True)
    Source.eStructuralFeatures.append(EAttribute('name', EString))
    fdsl.eClassifiers.append(Source)

    # SourceREST
    SourceREST = EClass('SourceREST')
    SourceREST.eSuperTypes.append(Source)
    SourceREST.eStructuralFeatures.append(EAttribute('url', EString))
    SourceREST.eStructuralFeatures.append(EAttribute('operations', Operation, upper=-1))
    fdsl.eClassifiers.append(SourceREST)

    # SourceWS
    SourceWS = EClass('SourceWS')
    SourceWS.eSuperTypes.append(Source)
    SourceWS.eStructuralFeatures.append(EAttribute('channel', EString))
    SourceWS.eStructuralFeatures.append(EAttribute('operations', Operation, upper=-1))
    fdsl.eClassifiers.append(SourceWS)

    # ==========================================================================
    # Entity Classes
    # ==========================================================================

    # TypeConstraint
    TypeConstraint = EClass('TypeConstraint')
    TypeConstraint.eStructuralFeatures.append(EAttribute('min', EFloat))
    TypeConstraint.eStructuralFeatures.append(EAttribute('max', EFloat))
    TypeConstraint.eStructuralFeatures.append(EAttribute('exact', EFloat))
    fdsl.eClassifiers.append(TypeConstraint)

    # TypeSpec
    TypeSpec = EClass('TypeSpec')
    TypeSpec.eStructuralFeatures.append(EAttribute('baseType', AttrType))
    TypeSpec.eStructuralFeatures.append(EAttribute('format', TypeFormat))
    TypeSpec.eStructuralFeatures.append(EAttribute('nullable', EBoolean))
    TypeSpec.eStructuralFeatures.append(EAttribute('readonly', EBoolean))
    TypeSpec.eStructuralFeatures.append(EAttribute('optional', EBoolean))
    fdsl.eClassifiers.append(TypeSpec)

    # Attribute
    Attribute = EClass('Attribute')
    Attribute.eStructuralFeatures.append(EAttribute('name', EString))
    fdsl.eClassifiers.append(Attribute)

    # ParentRef
    ParentRef = EClass('ParentRef')
    ParentRef.eStructuralFeatures.append(EAttribute('alias', EString))
    fdsl.eClassifiers.append(ParentRef)

    # Entity
    Entity = EClass('Entity')
    Entity.eStructuralFeatures.append(EAttribute('name', EString))
    Entity.eStructuralFeatures.append(EAttribute('ws_flow_type', WSFlowType))
    Entity.eStructuralFeatures.append(EAttribute('strict', EBoolean))
    fdsl.eClassifiers.append(Entity)

    # ==========================================================================
    # Expression Classes (simplified)
    # ==========================================================================

    # Expr (abstract base for expressions)
    Expr = EClass('Expr', abstract=True)
    fdsl.eClassifiers.append(Expr)

    # Literal
    Literal = EClass('Literal')
    Literal.eSuperTypes.append(Expr)
    Literal.eStructuralFeatures.append(EAttribute('stringValue', EString))
    Literal.eStructuralFeatures.append(EAttribute('intValue', EInt))
    Literal.eStructuralFeatures.append(EAttribute('floatValue', EFloat))
    Literal.eStructuralFeatures.append(EAttribute('boolValue', EBoolean))
    fdsl.eClassifiers.append(Literal)

    # Var
    Var = EClass('Var')
    Var.eSuperTypes.append(Expr)
    Var.eStructuralFeatures.append(EAttribute('name', EString))
    fdsl.eClassifiers.append(Var)

    # Call
    Call = EClass('Call')
    Call.eSuperTypes.append(Expr)
    Call.eStructuralFeatures.append(EAttribute('func', EString))
    fdsl.eClassifiers.append(Call)

    # BinaryExpr
    BinaryExpr = EClass('BinaryExpr')
    BinaryExpr.eSuperTypes.append(Expr)
    BinaryExpr.eStructuralFeatures.append(EAttribute('operator', EString))
    fdsl.eClassifiers.append(BinaryExpr)

    # UnaryExpr
    UnaryExpr = EClass('UnaryExpr')
    UnaryExpr.eSuperTypes.append(Expr)
    UnaryExpr.eStructuralFeatures.append(EAttribute('operator', EString))
    fdsl.eClassifiers.append(UnaryExpr)

    # IfThenElse
    IfThenElse = EClass('IfThenElse')
    IfThenElse.eSuperTypes.append(Expr)
    fdsl.eClassifiers.append(IfThenElse)

    # LambdaExpr
    LambdaExpr = EClass('LambdaExpr')
    LambdaExpr.eSuperTypes.append(Expr)
    LambdaExpr.eStructuralFeatures.append(EAttribute('param', EString))
    LambdaExpr.eStructuralFeatures.append(EAttribute('params', EString, upper=-1))
    fdsl.eClassifiers.append(LambdaExpr)

    # ==========================================================================
    # References (cross-references between classes)
    # ==========================================================================

    # FDSLModel containments
    FDSLModel.eStructuralFeatures.append(
        EReference('imports', Import, upper=-1, containment=True))
    FDSLModel.eStructuralFeatures.append(
        EReference('roles', Role, upper=-1, containment=True))
    FDSLModel.eStructuralFeatures.append(
        EReference('auth', Auth, upper=-1, containment=True))
    FDSLModel.eStructuralFeatures.append(
        EReference('servers', Server, upper=-1, containment=True))
    FDSLModel.eStructuralFeatures.append(
        EReference('sources', Source, upper=-1, containment=True))
    FDSLModel.eStructuralFeatures.append(
        EReference('entities', Entity, upper=-1, containment=True))

    # Auth containments
    Auth.eStructuralFeatures.append(
        EReference('jwt_config', JWTAuthConfig, containment=True))
    Auth.eStructuralFeatures.append(
        EReference('session_config', SessionAuthConfig, containment=True))

    # Server references
    Server.eStructuralFeatures.append(
        EReference('auth', Auth))  # non-containment reference

    # Entity containments and references
    Entity.eStructuralFeatures.append(
        EReference('parents', ParentRef, upper=-1, containment=True))
    Entity.eStructuralFeatures.append(
        EReference('source', Source))  # non-containment reference
    Entity.eStructuralFeatures.append(
        EReference('attributes', Attribute, upper=-1, containment=True))
    Entity.eStructuralFeatures.append(
        EReference('access', AccessBlock, containment=True))

    # ParentRef reference
    ParentRef.eStructuralFeatures.append(
        EReference('entity', Entity))  # non-containment reference

    # Attribute containments
    Attribute.eStructuralFeatures.append(
        EReference('type', TypeSpec, containment=True))
    Attribute.eStructuralFeatures.append(
        EReference('expr', Expr, containment=True))

    # TypeSpec containments and references
    TypeSpec.eStructuralFeatures.append(
        EReference('constraint', TypeConstraint, containment=True))
    TypeSpec.eStructuralFeatures.append(
        EReference('itemEntity', Entity))  # for array<Entity>
    TypeSpec.eStructuralFeatures.append(
        EReference('nestedEntity', Entity))  # for object<Entity>

    # AccessBlock references
    RoleBasedAccess.eStructuralFeatures.append(
        EReference('roles', Role, upper=-1))  # non-containment
    PerOperationAccess.eStructuralFeatures.append(
        EReference('rules', AccessRule, upper=-1, containment=True))
    AccessRule.eStructuralFeatures.append(
        EReference('roles', Role, upper=-1))  # non-containment

    # Expression references
    BinaryExpr.eStructuralFeatures.append(
        EReference('left', Expr, containment=True))
    BinaryExpr.eStructuralFeatures.append(
        EReference('right', Expr, containment=True))
    UnaryExpr.eStructuralFeatures.append(
        EReference('operand', Expr, containment=True))
    IfThenElse.eStructuralFeatures.append(
        EReference('condition', Expr, containment=True))
    IfThenElse.eStructuralFeatures.append(
        EReference('thenExpr', Expr, containment=True))
    IfThenElse.eStructuralFeatures.append(
        EReference('elseExpr', Expr, containment=True))
    Call.eStructuralFeatures.append(
        EReference('args', Expr, upper=-1, containment=True))
    LambdaExpr.eStructuralFeatures.append(
        EReference('body', Expr, containment=True))

    return fdsl


def save_ecore(package, output_path):
    """Save an EPackage to an .ecore file."""
    rset = ResourceSet()
    resource = rset.create_resource(URI(str(output_path)))
    resource.append(package)
    resource.save()
    print(f"Ecore metamodel saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Generate Ecore metamodel from FDSL textX grammar')
    parser.add_argument(
        '--output', '-o',
        default='docs/fdsl_metamodel.ecore',
        help='Output path for the .ecore file (default: docs/fdsl_metamodel.ecore)')

    args = parser.parse_args()

    # Create metamodel
    print("Creating FDSL Ecore metamodel (core classes)...")
    fdsl_package = create_fdsl_metamodel()

    # Summary
    classes = [c for c in fdsl_package.eClassifiers if isinstance(c, EClass)]
    enums = [c for c in fdsl_package.eClassifiers if isinstance(c, EEnum)]
    print(f"  - {len(classes)} EClasses")
    print(f"  - {len(enums)} EEnums")

    # Save
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_ecore(fdsl_package, output_path)


if __name__ == '__main__':
    main()
