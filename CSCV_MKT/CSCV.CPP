/******************************************************************************/
/*                                                                            */
/*  CSCV - Computationally symmetric cross validation.                        */
/*                                                                            */
/*  The core routine is in CSCV_CORE.CPP which handles any app                */
/*  This is the wrapper for applying CSCV to moving-average crossover         */
/*                                                                            */
/******************************************************************************/

#include <stdio.h>
#include <string.h>
#include <math.h>
#include <float.h>
#include <stdlib.h>
#include <conio.h>
#include <assert.h>

double cscvcore (
   int ncases ,         // Number of rows in returns matrix
   int n_systems ,      // Number of columns (competitors); should be large enough to reduce granularity
   int n_blocks ,       // Number of blocks (even!) into which the cases will be partitioned
   double *returns ,    // Ncases by n_systems matrix of returns
   int *indices ,       // Work vector n_blocks long
   int *lengths ,       // Work vector n_blocks long
   int *flags ,         // Work vector n_blocks long
   double *work ,       // Work vector ncases long
   double *is_crits ,   // Work vector n_systems long
   double *oos_crits    // Work vector n_systems long
   ) ;


/*
--------------------------------------------------------------------------------

   This is a random int generator suggested by Marsaglia in his DIEHARD suite.
   It provides a great combination of speed and quality.

   We also have unifrand(), a random 0-1 generator based on it.

--------------------------------------------------------------------------------
*/

static unsigned int Q[256], carry=362436 ;
static int MWC256_initialized = 0 ;
static int MWC256_seed = 123456789 ;

void RAND32M_seed ( int iseed ) { // Optionally set seed
   MWC256_seed = iseed ;
   MWC256_initialized = 0 ;
   }

unsigned int RAND32M ()
{
   unsigned _int64 t ;
   unsigned _int64 a=809430660 ;
   static unsigned char i=255 ;

   if (! MWC256_initialized) {
      unsigned int k,j=MWC256_seed ;
      MWC256_initialized = 1 ;
      for (k=0 ; k<256 ; k++) {
         j = 69069 * j + 12345 ; // This overflows, doing an automatic mod 2^32
         Q[k] = j ;
         }
      }

   t = a * Q[++i] + carry ;  // This is the 64-bit op, forced by a being 64-bit
   carry = (unsigned int) (t >> 32) ;
   Q[i] = (unsigned int) (t & 0xFFFFFFFF) ;
   return Q[i] ;
}


double unifrand ()
{
   static double mult = 1.0 / 0xFFFFFFFF ;
   return mult * RAND32M() ;
}


/*
--------------------------------------------------------------------------------

   Local routine computes one-bar returns for all short-term and
   long-term lookbacks of a primitive moving-average crossover system.
   The computed returns matrix has max_lookback * (max_lookback-1) / 2 rows
   and nprices-max_lookback columns, which change fastest.
   Note that this is the transpose of the matrix in the original paper.

--------------------------------------------------------------------------------
*/

/*
   get_returns function removed to avoid duplicate symbol with CSCV_MKT.CPP
   The function is defined in CSCV_MKT.CPP which is the main application file
*/


/*
--------------------------------------------------------------------------------

   Optional main routine for testing with random numbers (commented out to avoid duplicate symbols)

--------------------------------------------------------------------------------
*/

/*
--------------------------------------------------------------------------------

   Optional main routine for testing with random numbers (completely removed to avoid duplicate symbols)

--------------------------------------------------------------------------------
*/
